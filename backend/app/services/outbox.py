"""Reliable email delivery.

Every email is written to the email_outbox table first, then sent in the
background. A failed send records the error and is retried with backoff
(1 min, 5 min, 15 min, 1 h, 6 h); after the last attempt it is marked "dead".
Admins can list failures and re-send them (see /admin/notifications).
"""
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.outbox import EmailOutbox

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = [60, 300, 900, 3600, 21600]
_worker_started = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue_email(category: str, to_email: str, to_name: str | None, subject: str, html: str,
                  send_now: bool = True) -> int:
    """Store the email, then send it in the background. With send_now=False the caller
    delivers it (bulk mail is sent one by one so the SMTP server isn't flooded)."""
    with SessionLocal() as db:
        row = EmailOutbox(
            category=category, to_email=to_email, to_name=to_name, subject=subject, html=html,
            status="pending", attempts=0, next_attempt_at=_now(),
        )
        db.add(row)
        db.commit()
        row_id = row.id
    if send_now:
        threading.Thread(target=deliver, args=(row_id,), daemon=True).start()
    return row_id


def deliver(outbox_id: int, force: bool = False) -> bool:
    from app.services.email import send_raw

    with SessionLocal() as db:
        row = db.get(EmailOutbox, outbox_id)
        if not row or row.status == "sent":
            return bool(row)
        if row.status == "dead" and not force:
            return False
        ok, error = send_raw(row.to_email, row.to_name or "", row.subject, row.html)
        row.attempts = (row.attempts or 0) + 1
        if ok:
            row.status, row.sent_at, row.last_error, row.next_attempt_at = "sent", _now(), None, None
        else:
            row.last_error = (error or "unknown error")[:1000]
            if row.attempts >= settings.EMAIL_MAX_ATTEMPTS:
                row.status, row.next_attempt_at = "dead", None
                logger.error("[EMAIL] giving up on #%s to %s after %s attempts: %s",
                             row.id, row.to_email, row.attempts, row.last_error)
            else:
                delay = BACKOFF_SECONDS[min(row.attempts - 1, len(BACKOFF_SECONDS) - 1)]
                row.status, row.next_attempt_at = "failed", _now() + timedelta(seconds=delay)
        db.commit()
        return ok


def retry_due(limit: int = 50) -> int:
    """Re-send failed emails whose backoff has elapsed, plus pending ones that were
    never attempted (e.g. the process restarted mid-send)."""
    now = _now()
    stale_pending = now - timedelta(minutes=5)
    with SessionLocal() as db:
        ids = [r.id for r in db.query(EmailOutbox.id).filter(or_(
            (EmailOutbox.status == "failed") & (EmailOutbox.next_attempt_at <= now),
            (EmailOutbox.status == "pending") & (EmailOutbox.created_at <= stale_pending),
        )).order_by(EmailOutbox.id).limit(limit).all()]
    for i in ids:
        deliver(i)
    return len(ids)


def _worker_loop(interval: int) -> None:
    while True:
        time.sleep(interval)
        try:
            retried = retry_due()
            if retried:
                logger.info("[EMAIL] retried %s queued email(s)", retried)
        except Exception:
            logger.exception("[EMAIL] retry worker error")


def start_retry_worker(interval: int = 60) -> None:
    global _worker_started
    if _worker_started:
        return
    _worker_started = True
    threading.Thread(target=_worker_loop, args=(interval,), daemon=True, name="email-retry").start()
