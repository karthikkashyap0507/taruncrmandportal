from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.deps import get_current_user, require_owner, require_owner_or_bdm
from app.models import (
    Lead, Candidate, CRMJob, Application, Interview,
    LeadStatus, CandidateStatus, JobStatus, InterviewStatus, User,
    Invoice, InvoiceStatus, Placement, PlacementStatus, UserRole,
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
    days: int = Query(30, ge=1, le=3650),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """Per-person activity over the period: leads, placements, joinings (owner only)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    users = (await db.execute(select(User).where(User.is_active == True))).scalars().all()  # noqa: E712
    leads = dict((await db.execute(select(Lead.assigned_to_id, func.count(Lead.id))
                                   .where(Lead.created_at >= cutoff).group_by(Lead.assigned_to_id))).all())
    offers = dict((await db.execute(select(Placement.recruiter_id, func.count(Placement.id))
                                    .where(Placement.created_at >= cutoff).group_by(Placement.recruiter_id))).all())
    joined = dict((await db.execute(select(Placement.recruiter_id, func.count(Placement.id))
                                    .where(Placement.joined_on >= cutoff).group_by(Placement.recruiter_id))).all())
    rows = [{
        "user_id": u.id, "name": u.name, "role": u.role.value,
        "leads_assigned": leads.get(u.id, 0), "offers": offers.get(u.id, 0), "joined": joined.get(u.id, 0),
    } for u in users]
    return sorted(rows, key=lambda r: (r["joined"], r["offers"], r["leads_assigned"]), reverse=True)


@router.get("/revenue")
async def revenue_analytics(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_owner_or_bdm)):
    """Billing from real invoices, plus the lead pipeline value (owners and BDMs)."""
    now = datetime.now(timezone.utc)

    async def total(*conds):
        q = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(*conds)
        return round(float((await db.execute(q)).scalar() or 0), 2)

    pipeline = (await db.execute(select(func.coalesce(func.sum(Lead.budget), 0))
                                 .where(Lead.status.in_([LeadStatus.proposal, LeadStatus.negotiation])))).scalar()
    converted = (await db.execute(select(func.coalesce(func.sum(Lead.budget), 0)).where(Lead.converted == True))).scalar()  # noqa: E712
    return {
        "invoiced": await total(Invoice.status != InvoiceStatus.cancelled),
        "collected": await total(Invoice.status == InvoiceStatus.paid),
        "outstanding": await total(Invoice.status == InvoiceStatus.sent),
        "overdue": await total(Invoice.status == InvoiceStatus.sent, Invoice.due_date < now),
        "total_pipeline_value": float(converted or 0),
        "proposal_value": float(pipeline or 0),
        "currency": "INR",
    }


@router.get("/revenue/monthly")
async def revenue_monthly(months: int = Query(12, ge=1, le=36), db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(require_owner_or_bdm)):
    """Invoiced vs collected per month (bucketed in Python: works on SQLite and Postgres)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=31 * months)
    rows = (await db.execute(select(Invoice).where(Invoice.issue_date >= cutoff,
                                                   Invoice.status != InvoiceStatus.cancelled))).scalars().all()
    buckets: dict[str, dict] = {}
    for inv in rows:
        key = inv.issue_date.strftime("%Y-%m")
        b = buckets.setdefault(key, {"month": key, "invoiced": 0.0, "collected": 0.0, "count": 0})
        b["invoiced"] += inv.total_amount
        b["count"] += 1
        if inv.status == InvoiceStatus.paid:
            b["collected"] += inv.total_amount
    return [{**b, "invoiced": round(b["invoiced"], 2), "collected": round(b["collected"], 2)}
            for _, b in sorted(buckets.items())]


@router.get("/placements/summary")
async def placements_summary(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Placement funnel (HR users see their own numbers)."""
    q = select(Placement.status, func.count(Placement.id)).group_by(Placement.status)
    if current_user.role == UserRole.hr:
        q = q.where(Placement.recruiter_id == current_user.id)
    counts = {s.value: 0 for s in PlacementStatus}
    for status, n in (await db.execute(q)).all():
        counts[status.value] = n
    return counts
