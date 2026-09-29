from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Task, TaskPriority, TaskStatus, User

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.medium
    assigned_to_id: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    assigned_to_id: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    completed_at: Optional[datetime] = None


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


@router.get("/")
async def list_tasks(
    status: Optional[str] = None,
    assigned_to_me: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Task)
    if assigned_to_me:
        query = query.where(Task.assigned_to_id == current_user.id)
    if status:
        query = query.where(Task.status == status)
    query = query.order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())
    result = await db.execute(query)
    return [_serialize(t) for t in result.scalars().all()]


@router.post("/", status_code=201)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(**payload.model_dump(exclude_none=True), created_by_id=current_user.id, status=TaskStatus.todo)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _serialize(task)


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(task, field, val)
    if payload.status == TaskStatus.done and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return _serialize(task)


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted"}
