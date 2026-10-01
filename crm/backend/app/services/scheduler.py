"""Background jobs, run every SCHEDULER_INTERVAL_SECONDS inside the API process.

- re-send failed emails (outbox backoff)
- follow-up reminders (15 min before they are due)
- interview reminders (24 h before)
- joining reminders (expected joining date within 24 h)
- overdue invoice alerts
- expire MOUs whose end date has passed
Each reminder is sent once (a *_sent_at / reminded_at flag is stored).
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import (
    Agreement, AgreementStatus, Candidate, Company, CRMJob, FollowUp, Interview, InterviewStatus, Invoice,
    InvoiceStatus, Lead, NotifType, Placement, PlacementStatus, User, UserRole,
)
from app.services import email as mail
from app.services import outbox
from app.services.activity import notify

logger = logging.getLogger(__name__)


async def _staff(db, roles) -> list[int]:
    return [r[0] for r in (await db.execute(
        select(User.id).where(User.role.in_(roles), User.is_active == True))).all()]  # noqa: E712


async def run_once() -> dict:
    now = datetime.now(timezone.utc)
    stats = {"emails_retried": await asyncio.to_thread(outbox.retry_due)}
    emails = []  # (function, args) queued after commit

    async with AsyncSessionLocal() as db:
        # Follow-up reminders
        fups = (await db.execute(select(FollowUp, Lead).join(Lead, Lead.id == FollowUp.lead_id).where(
            FollowUp.completed == False, FollowUp.reminded_at.is_(None),  # noqa: E712
            FollowUp.scheduled_at <= now + timedelta(minutes=15)))).all()
        for fup, lead in fups:
            fup.reminded_at = now
            ids = notify(db, [fup.created_by_id, lead.assigned_to_id], f"Follow-up due: {lead.company_name}",
                         f"{fup.type} at {fup.scheduled_at:%d %b %H:%M}", NotifType.follow_up, f"/leads/{lead.id}")
            for uid in ids:
                u = await db.get(User, uid)
                if u:
                    emails.append((mail.send_followup_reminder_email,
                                   (u.email, u.name, lead.company_name, fup.type, fup.scheduled_at)))
        stats["followup_reminders"] = len(fups)

        # Interview reminders (24 h ahead)
        ivs = (await db.execute(select(Interview).where(
            Interview.status.in_([InterviewStatus.scheduled, InterviewStatus.rescheduled]),
            Interview.reminder_sent_at.is_(None),
            Interview.scheduled_at > now, Interview.scheduled_at <= now + timedelta(hours=24)))).scalars().all()
        for iv in ivs:
            iv.reminder_sent_at = now
            cand = await db.get(Candidate, iv.candidate_id)
            interviewer_ids = [u.id for u in await db.run_sync(lambda s, iv=iv: list(iv.interviewers))]
            notify(db, [*interviewer_ids, iv.scheduled_by_id], f"Interview tomorrow: {cand.name if cand else ''}",
                   f"{iv.scheduled_at:%d %b %H:%M}", NotifType.interview_reminder, "/interviews")
            if cand and cand.email:
                emails.append((mail.send_interview_reminder_email, (cand.email, cand.name, iv)))
        stats["interview_reminders"] = len(ivs)

        # Joining reminders
        pls = (await db.execute(select(Placement).where(
            Placement.status == PlacementStatus.offered, Placement.joining_reminder_sent_at.is_(None),
            Placement.expected_joining_date.isnot(None),
            Placement.expected_joining_date <= now + timedelta(hours=24)))).scalars().all()
        for pl in pls:
            pl.joining_reminder_sent_at = now
            cand, comp = await db.get(Candidate, pl.candidate_id), await db.get(Company, pl.company_id)
            notify(db, [pl.recruiter_id, pl.bdm_id], f"Joining due: {cand.name if cand else ''}",
                   f"{comp.name if comp else ''} on {pl.expected_joining_date:%d %b %Y} - confirm the joining",
                   NotifType.joining, "/placements")
            if cand and cand.email:
                emails.append((mail.send_joining_reminder_email,
                               (cand.email, cand.name, comp.name if comp else "", pl.expected_joining_date)))
        stats["joining_reminders"] = len(pls)

        # Overdue invoices
        invs = (await db.execute(select(Invoice).where(
            Invoice.status == InvoiceStatus.sent, Invoice.due_date < now,
            Invoice.overdue_notified_at.is_(None)))).scalars().all()
        if invs:
            staff = await _staff(db, (UserRole.owner, UserRole.bdm))
            for inv in invs:
                inv.overdue_notified_at = now
                notify(db, staff, f"Invoice overdue: {inv.invoice_number}",
                       f"INR {inv.total_amount:,.2f} was due {inv.due_date:%d %b %Y}", NotifType.invoice, "/invoices")
        stats["overdue_invoices"] = len(invs)

        # Expire MOUs past their end date
        agrs = (await db.execute(select(Agreement).where(
            Agreement.status == AgreementStatus.active, Agreement.end_date.isnot(None),
            Agreement.end_date < now))).scalars().all()
        if agrs:
            owners = await _staff(db, (UserRole.owner,))
            for a in agrs:
                a.status = AgreementStatus.expired
                notify(db, owners, f"MOU expired: {a.title}", "Renew it to keep billing new placements",
                       NotifType.system, "/agreements")
        stats["agreements_expired"] = len(agrs)
        await db.commit()

    for func, args in emails:
        try:
            await asyncio.to_thread(func, *args)
        except Exception:
            logger.exception("reminder email failed to queue")
    return stats


async def scheduler_loop() -> None:
    await asyncio.sleep(min(10, settings.SCHEDULER_INTERVAL_SECONDS))
    while True:
        try:
            stats = await run_once()
            if any(v for v in stats.values()):
                logger.info("scheduler: %s", stats)
        except Exception:
            logger.exception("scheduler run failed")
        await asyncio.sleep(settings.SCHEDULER_INTERVAL_SECONDS)
