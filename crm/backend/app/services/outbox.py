"""Reliable email delivery for the CRM.

Every email is written to crm_email_outbox first, then sent in the background.
A failed send records the error and is retried with backoff (1 min, 5 min,
15 min, 1 h, 6 h); after the last attempt it is marked "dead". The owner can
list failures and re-send them (see /notifications/deliveries).
"""
import logging
import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_

from app.core.config import settings
from app.core.database import SyncSessionLocal
from app.models import EmailOutbox

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = [60, 300, 900, 3600, 21600]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue_email(category: str, to_email: str, to_name: str | None, subject: str, html: str) -> int:
    with SyncSessionLocal() as db:
        row = EmailOutbox(category=category, to_email=to_email, to_name=to_name, subject=subject,
                          html=html, status="pending", attempts=0, next_attempt_at=_now())
        db.add(row)
        db.commit()
        row_id = row.id
    threading.Thread(target=deliver, args=(row_id,), daemon=True).start()
    return row_id


def deliver(outbox_id: int, force: bool = False) -> bool:
    from app.services.email import send_raw

    with SyncSessionLocal() as db:
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
    """Re-send failed emails whose backoff has elapsed, plus pending ones never attempted."""
    now = _now()
    with SyncSessionLocal() as db:
        ids = [r.id for r in db.query(EmailOutbox.id).filter(or_(
            (EmailOutbox.status == "failed") & (EmailOutbox.next_attempt_at <= now),
            (EmailOutbox.status == "pending") & (EmailOutbox.created_at <= now - timedelta(minutes=5)),
        )).order_by(EmailOutbox.id).limit(limit).all()]
    for i in ids:
        deliver(i)
    return len(ids)
