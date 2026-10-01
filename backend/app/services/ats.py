"""ATS workflow rules for application status changes.

Applications move forward: applied -> screening -> interview -> offered -> hired
(stages may be skipped, except that "hired" requires an offer first). Any open
application can be rejected; a rejected one can be reopened to applied or
screening. Only the candidate can withdraw. hired and withdrawn are final.
Every change is recorded in application_events.
"""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus as S
from app.models.application_event import ApplicationEvent

_ORDER = {S.applied: 0, S.screening: 1, S.interview: 2, S.offered: 3, S.hired: 4}
FINAL = {S.hired, S.withdrawn}


def check_transition(current: S, target: S, by_candidate: bool = False) -> str | None:
    """Return None if allowed, otherwise a human-readable reason."""
    if current == target:
        return f"The application is already in {target.value}"
    if current in FINAL:
        return f"The application is already {current.value} and can no longer be changed"
    if by_candidate:
        return None if target == S.withdrawn else "Candidates can only withdraw an application"
    if target == S.withdrawn:
        return "Only the candidate can withdraw an application"
    if target == S.rejected:
        return None
    if current == S.rejected:
        return None if target in (S.applied, S.screening) else "Reopen the application (move it to screening) first"
    if target == S.hired and current != S.offered:
        return "A candidate can only be marked hired after an offer"
    if _ORDER[target] > _ORDER[current]:
        return None
    return f"An application cannot move back from {current.value} to {target.value}"


def change_status(db: Session, app: Application, target: S, actor_user_id: int | None,
                  note: str | None = None, by_candidate: bool = False) -> S:
    """Apply a validated status change and record it. Raises 409 if not allowed."""
    current = S(app.status)
    reason = check_transition(current, target, by_candidate)
    if reason:
        raise HTTPException(status_code=409, detail=reason)
    app.status = target
    app.status_changed_at = datetime.now(timezone.utc)
    db.add(ApplicationEvent(application_id=app.id, from_status=current.value, to_status=target.value,
                            actor_user_id=actor_user_id, note=(note or None)))
    return current


def record_applied(db: Session, app: Application, actor_user_id: int) -> None:
    db.add(ApplicationEvent(application_id=app.id, from_status=None, to_status=S.applied.value,
                            actor_user_id=actor_user_id))
