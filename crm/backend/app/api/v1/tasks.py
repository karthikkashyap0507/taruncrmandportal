from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, is_owner
from app.models import ActivityType, NotifType, Task, TaskPriority, TaskStatus, User
from app.services.activity import diff, log_activity, notify, queue_email

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10000)
    priority: TaskPriority = TaskPriority.medium
    assigned_to_id: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10000)
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    assigned_to_id: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


def _serialize(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "priority": t.priority.value,
        "status": t.status.value,
        "assigned_to_id": t.assigned_to_id,
        "created_by_id": t.created_by_id,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "tags": t.tags or [],
        "created_at": t.created_at.isoformat(),
    }


def _visible(query, user: User):
    """Owners see every task; everyone else sees tasks assigned to or created by them."""
    if is_owner(user):
        return query
    return query.where(or_(Task.assigned_to_id == user.id, Task.created_by_id == user.id))


async def _get_task(db: AsyncSession, task_id: int, user: User) -> Task:
    task = (await db.execute(_visible(select(Task).where(Task.id == task_id), user))).scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    return task


async def _check_assignee(db: AsyncSession, user_id: Optional[int]) -> Optional[User]:
    if user_id is None:
        return None
    target = await db.get(User, user_id)
    if not target or not target.is_active:
        raise HTTPException(400, "The selected team member doesn't exist or is inactive")
    return target


async def _email_assignee(task: Task, assignee: Optional[User], actor: User) -> None:
    if assignee and assignee.id != actor.id:
        from app.services.email import send_task_assigned_email
        await queue_email(send_task_assigned_email, assignee.email, assignee.name, task.title, task.due_date)


@router.get("/")
async def list_tasks(
    status: Optional[str] = None,
    assigned_to_me: bool = False,
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _visible(select(Task), current_user)
    if assigned_to_me:
        query = query.where(Task.assigned_to_id == current_user.id)
    if status:
        query = query.where(Task.status == status)
    query = query.order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc()).limit(limit)
    return [_serialize(t) for t in (await db.execute(query)).scalars().all()]


@router.post("/", status_code=201)
async def create_task(payload: TaskCreate, request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    assignee = await _check_assignee(db, payload.assigned_to_id)
    task = Task(**payload.model_dump(exclude_none=True), created_by_id=current_user.id, status=TaskStatus.todo)
    db.add(task)
    await db.flush()
    log_activity(db, current_user, ActivityType.create, f"Created task {task.title}", "task", task.id,
                 request=request)
    notify(db, [task.assigned_to_id], "New task assigned to you", task.title, NotifType.task_assigned, "/tasks",
           exclude=current_user.id)
    await db.commit()
    await db.refresh(task)
    await _email_assignee(task, assignee, current_user)
    return _serialize(task)


@router.put("/{task_id}")
async def update_task(task_id: int, payload: TaskUpdate, request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    task = await _get_task(db, task_id, current_user)
    data = payload.model_dump(exclude_none=True)
    assignee = None
    if "assigned_to_id" in data and data["assigned_to_id"] != task.assigned_to_id:
        if not (is_owner(current_user) or task.created_by_id == current_user.id):
            raise HTTPException(403, "Only the task creator or an owner can reassign this task")
        assignee = await _check_assignee(db, data["assigned_to_id"])
    changes = diff(task, data)
    for field, val in data.items():
        setattr(task, field, val)
    if payload.status == TaskStatus.done and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    if changes:
        log_activity(db, current_user, ActivityType.update, f"Updated task {task.title}", "task", task.id,
                     changes=changes, request=request)
    if assignee:
        notify(db, [assignee.id], "Task assigned to you", task.title, NotifType.task_assigned, "/tasks",
               exclude=current_user.id)
    if payload.status == TaskStatus.done and task.created_by_id != current_user.id:
        notify(db, [task.created_by_id], "Task completed", task.title, NotifType.status_changed, "/tasks")
    await db.commit()
    await _email_assignee(task, assignee, current_user)
    return _serialize(task)


@router.delete("/{task_id}")
async def delete_task(task_id: int, request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    task = await _get_task(db, task_id, current_user)
    if not (is_owner(current_user) or task.created_by_id == current_user.id):
        raise HTTPException(403, "Only the task creator or an owner can delete this task")
    log_activity(db, current_user, ActivityType.delete, f"Deleted task {task.title}", "task", task.id,
                 request=request)
    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted"}
