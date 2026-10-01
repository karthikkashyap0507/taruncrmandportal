"""CSV report exports (same visibility rules as the rest of the CRM; every export is audited)."""
import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, is_owner
from app.models import (
    ActivityType, Candidate, Company, CRMJob, Incentive, Invoice, Lead, Placement, User, UserRole,
)
from app.services.activity import log_activity

router = APIRouter(prefix="/reports", tags=["reports"])

MAX_ROWS = 50000


def _csv(filename: str, header: list[str], rows) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else (v.isoformat() if isinstance(v, datetime) else v) for v in r])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def _range(q, column, since, until):
    if since:
        q = q.where(column >= since)
    if until:
        q = q.where(column <= until)
    return q


@router.get("/{report}.csv")
async def export(
    report: str,
    request: Request,
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = current_user.role
    if report == "leads":
        q = _range(select(Lead), Lead.created_at, since, until)
        if role == UserRole.hr:
            q = q.where(Lead.assigned_to_id == current_user.id)
        rows = (await db.execute(q.order_by(Lead.id).limit(MAX_ROWS))).scalars().all()
        resp = _csv("leads.csv", ["id", "company", "contact", "email", "phone", "status", "temperature", "source",
                                  "budget", "assigned_to_id", "created_at"],
                    [(l.id, l.company_name, l.contact_name, l.contact_email, l.contact_phone, l.status.value,
                      l.temperature.value, l.source, l.budget, l.assigned_to_id, l.created_at) for l in rows])
    elif report == "candidates":
        q = _range(select(Candidate), Candidate.created_at, since, until)
        rows = (await db.execute(q.order_by(Candidate.id).limit(MAX_ROWS))).scalars().all()
        resp = _csv("candidates.csv", ["id", "name", "email", "phone", "title", "company", "experience_years",
                                       "status", "source", "ats_score", "created_at"],
                    [(c.id, c.name, c.email, c.phone, c.current_title, c.current_company, c.experience_years,
                      c.status.value, c.source, c.ats_score, c.created_at) for c in rows])
    elif report == "placements":
        q = _range(select(Placement, Candidate.name, CRMJob.title, Company.name)
                   .join(Candidate, Candidate.id == Placement.candidate_id)
                   .join(CRMJob, CRMJob.id == Placement.job_id)
                   .join(Company, Company.id == Placement.company_id), Placement.offer_date, since, until)
        if role == UserRole.hr:
            q = q.where(Placement.recruiter_id == current_user.id)
        rows = (await db.execute(q.order_by(Placement.id).limit(MAX_ROWS))).all()
        resp = _csv("placements.csv", ["id", "candidate", "job", "client", "status", "offered_ctc", "fee_amount",
                                       "offer_date", "expected_joining", "joined_on", "recruiter_id", "bdm_id"],
                    [(p.id, cn, jt, co, p.status.value, p.offered_ctc, p.fee_amount, p.offer_date,
                      p.expected_joining_date, p.joined_on, p.recruiter_id, p.bdm_id) for p, cn, jt, co in rows])
    elif report == "invoices":
        if role == UserRole.hr:
            raise HTTPException(403, "You don't have permission to export invoices")
        q = _range(select(Invoice, Company.name).join(Company, Company.id == Invoice.company_id),
                   Invoice.issue_date, since, until)
        rows = (await db.execute(q.order_by(Invoice.id).limit(MAX_ROWS))).all()
        resp = _csv("invoices.csv", ["invoice_number", "client", "amount", "gst", "total", "status", "issue_date",
                                     "due_date", "paid_on", "overridden", "override_reason"],
                    [(i.invoice_number, co, i.amount, i.gst_amount, i.total_amount, i.status.value, i.issue_date,
                      i.due_date, i.paid_on, i.amount_overridden, i.override_reason) for i, co in rows])
    elif report == "incentives":
        q = _range(select(Incentive, User.name).join(User, User.id == Incentive.user_id),
                   Incentive.created_at, since, until)
        if not is_owner(current_user):
            q = q.where(Incentive.user_id == current_user.id)
        rows = (await db.execute(q.order_by(Incentive.id).limit(MAX_ROWS))).all()
        resp = _csv("incentives.csv", ["id", "person", "role", "invoice_id", "basis_amount", "rate", "amount",
                                       "status", "created_at"],
                    [(i.id, n, i.role.value, i.invoice_id, i.basis_amount, i.rate, i.amount, i.status.value,
                      i.created_at) for i, n in rows])
    else:
        raise HTTPException(404, "Unknown report. Available: leads, candidates, placements, invoices, incentives")

    log_activity(db, current_user, ActivityType.export, f"Exported {report}.csv", "report", None, request=request)
    await db.commit()
    return resp
