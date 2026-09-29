from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    Lead, Candidate, CRMJob, Application, Interview,
    LeadStatus, CandidateStatus, JobStatus, InterviewStatus, User
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Leads stats
    total_leads = (await db.execute(select(func.count(Lead.id)))).scalar()
    new_leads = (await db.execute(select(func.count(Lead.id)).where(Lead.status == LeadStatus.new))).scalar()
    converted_leads = (await db.execute(select(func.count(Lead.id)).where(Lead.converted == True))).scalar()
    leads_this_month = (await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= month_start)
    )).scalar()

    # Candidates stats
    total_candidates = (await db.execute(select(func.count(Candidate.id)))).scalar()
    active_candidates = (await db.execute(
        select(func.count(Candidate.id)).where(Candidate.status.notin_([CandidateStatus.rejected, CandidateStatus.placed]))
    )).scalar() or 0
    placed_candidates = (await db.execute(
        select(func.count(Candidate.id)).where(Candidate.status == CandidateStatus.placed)
    )).scalar() or 0

    # Jobs stats
    open_jobs = (await db.execute(select(func.count(CRMJob.id)).where(CRMJob.status == JobStatus.open))).scalar() or 0
    total_jobs = (await db.execute(select(func.count(CRMJob.id)))).scalar()

    # Interviews
    scheduled_interviews = (await db.execute(
        select(func.count(Interview.id)).where(Interview.status == InterviewStatus.scheduled)
    )).scalar()
    interviews_today = (await db.execute(
        select(func.count(Interview.id)).where(
            Interview.scheduled_at >= now.replace(hour=0, minute=0, second=0),
            Interview.scheduled_at < now.replace(hour=23, minute=59, second=59),
        )
    )).scalar()

    conversion_rate = round((converted_leads / total_leads * 100), 1) if total_leads else 0

    return {
        "leads": {
            "total": total_leads,
            "new": new_leads,
            "converted": converted_leads,
            "this_month": leads_this_month,
            "conversion_rate": conversion_rate,
        },
        "candidates": {
            "total": total_candidates,
            "active": active_candidates,
            "placed": placed_candidates,
        },
        "jobs": {
            "total": total_jobs,
            "open": open_jobs,
        },
        "interviews": {
            "scheduled": scheduled_interviews,
            "today": interviews_today,
        },
    }


@router.get("/leads/pipeline")
async def leads_pipeline(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    rows = result.all()
    return [{"status": r[0].value, "count": r[1]} for r in rows]


@router.get("/leads/trend")
async def leads_trend(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    # Bucket by day in Python so this works on both SQLite and PostgreSQL
    # (date_trunc is Postgres-only and errors on SQLite).
    result = await db.execute(
        select(Lead.created_at).where(Lead.created_at >= cutoff).order_by(Lead.created_at)
    )
    counts: dict[str, int] = {}
    for (created_at,) in result.all():
        if created_at is None:
            continue
        day = created_at.date().isoformat()
        counts[day] = counts.get(day, 0) + 1
    return [{"date": d, "count": c} for d, c in sorted(counts.items())]


@router.get("/candidates/by-status")
async def candidates_by_status(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Candidate.status, func.count(Candidate.id)).group_by(Candidate.status)
    )
    return [{"status": r[0].value, "count": r[1]} for r in result.all()]


@router.get("/team/performance")
async def team_performance(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            User.id,
            User.name,
            User.role,
            func.count(Lead.id).label("leads_count"),
        )
        .join(Lead, Lead.assigned_to_id == User.id, isouter=True)
        .where(Lead.created_at >= cutoff)
        .group_by(User.id, User.name, User.role)
        .order_by(func.count(Lead.id).desc())
    )
    rows = result.all()
    return [
        {
            "user_id": r[0],
            "name": r[1],
            "role": r[2].value,
            "leads_assigned": r[3],
        }
        for r in rows
    ]


@router.get("/revenue")
async def revenue_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(func.sum(Lead.budget)).where(Lead.converted == True))
    total_pipeline = result.scalar() or 0

    result2 = await db.execute(select(func.sum(Lead.budget)).where(Lead.status == LeadStatus.negotiation))
    proposal_value = result2.scalar() or 0

    return {
        "total_pipeline_value": float(total_pipeline),
        "proposal_value": float(proposal_value),
        "currency": "INR",
    }
