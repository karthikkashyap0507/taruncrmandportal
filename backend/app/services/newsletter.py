"""Weekly job-alert newsletter.

Sign-up is double opt-in: the confirmation and unsubscribe links carry an HMAC of
the address, so they can't be forged for someone else. Every Monday from 09:00 IST
each confirmed subscriber gets one email with the jobs posted in the last 7 days.
A subscriber is "claimed" with an atomic UPDATE before their email is queued, so
the same week's email is never sent twice, even with several API processes.
"""
import hashlib
import hmac
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from sqlalchemy import or_, update
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enquiry import NewsletterSubscriber
from app.models.job import Job, JobStatus

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
DIGEST_WEEKDAY = 0          # Monday
DIGEST_HOUR = 9             # 09:00 IST
DIGEST_MAX_JOBS = 10
SEND_GAP_SECONDS = 0.5      # pause between bulk emails so the SMTP server isn't flooded
_worker_started = False


def sign(action: str, email: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"newsletter:{action}:{email}".encode(), hashlib.sha256).hexdigest()


def verify(action: str, email: str, sig: str) -> bool:
    return hmac.compare_digest(sign(action, email), sig or "")


def link(action: str, email: str) -> str:
    """Website link for "confirm" or "unsubscribe"; the page posts it back to the API."""
    return f"{settings.FRONTEND_URL}/newsletter?{urlencode({'action': action, 'email': email, 'sig': sign(action, email)})}"


def week_start(now: datetime) -> datetime | None:
    """This week's send time (Monday 09:00 IST) in UTC, or None if it hasn't arrived yet."""
    local = now.astimezone(IST)
    start = (local - timedelta(days=(local.weekday() - DIGEST_WEEKDAY) % 7)).replace(
        hour=DIGEST_HOUR, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc) if local >= start else None


def _recent_jobs(db, now: datetime) -> list[dict]:
    rows = (db.query(Job).options(joinedload(Job.company))
            .filter(Job.status == JobStatus.published, Job.created_at >= now - timedelta(days=7))
            .order_by(Job.created_at.desc()).limit(DIGEST_MAX_JOBS).all())
    return [{
        "title": j.title, "company": j.company.name if j.company else None, "location": j.location,
        "employment_type": j.employment_type, "salary_min": j.salary_min, "salary_max": j.salary_max,
        "url": f"{settings.FRONTEND_URL}/jobs/{j.id}",
    } for j in rows]


def queue_digest(now: datetime | None = None, force: bool = False) -> tuple[list[int], int]:
    """Queue this week's email for every confirmed subscriber who hasn't had it.

    Returns (outbox ids, number of jobs in the email). force=True is the admin's
    "send now": it ignores the Monday schedule but still skips anyone who got an
    alert in the last 6 days, so pressing it twice doesn't double-send.
    """
    from app.services.email import build_digest_email
    from app.services.outbox import enqueue_email

    now = now or datetime.now(timezone.utc)
    if force:
        cutoff, confirmed_before = now - timedelta(days=6), now
    else:
        cutoff = week_start(now)
        if cutoff is None:
            return [], 0
        confirmed_before = cutoff  # people who join mid-week start with next Monday's email

    with SessionLocal() as db:
        jobs = _recent_jobs(db, now)
        if not jobs:
            return [], 0
        due = or_(NewsletterSubscriber.last_digest_at.is_(None), NewsletterSubscriber.last_digest_at < cutoff)
        candidates = db.query(NewsletterSubscriber.id, NewsletterSubscriber.email).filter(
            NewsletterSubscriber.confirmed_at.isnot(None),
            NewsletterSubscriber.confirmed_at <= confirmed_before,
            NewsletterSubscriber.unsubscribed_at.is_(None),
            due,
        ).order_by(NewsletterSubscriber.id).all()

        queued = []
        for sub_id, email in candidates:
            claimed = db.execute(
                update(NewsletterSubscriber)
                .where(NewsletterSubscriber.id == sub_id, NewsletterSubscriber.unsubscribed_at.is_(None), due)
                .values(last_digest_at=now)
            ).rowcount
            db.commit()
            if not claimed:
                continue
            subject, html = build_digest_email(jobs, link("unsubscribe", email))
            queued.append(enqueue_email("newsletter_digest", email, None, subject, html, send_now=False))
    return queued, len(jobs)


def deliver_slowly(outbox_ids: list[int]) -> None:
    """Send queued bulk emails one at a time. Failures stay in the outbox and are retried."""
    from app.services.outbox import deliver

    for i in outbox_ids:
        try:
            deliver(i)
        except Exception:
            logger.exception("[NEWSLETTER] could not send outbox #%s", i)
        time.sleep(SEND_GAP_SECONDS)


def _worker_loop(interval: int) -> None:
    while True:
        try:
            ids, _ = queue_digest()
            if ids:
                logger.info("[NEWSLETTER] sending this week's job alert to %s subscriber(s)", len(ids))
                deliver_slowly(ids)
        except Exception:
            logger.exception("[NEWSLETTER] weekly digest error")
        time.sleep(interval)


def start_digest_worker(interval: int = 900) -> None:
    global _worker_started
    if _worker_started:
        return
    _worker_started = True
    threading.Thread(target=_worker_loop, args=(interval,), daemon=True, name="newsletter-digest").start()
