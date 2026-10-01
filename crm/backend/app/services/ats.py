"""CRM ATS workflow: allowed application stages and transitions.

Applications move forward: applied -> screening -> interview -> offer -> hired
(stages may be skipped, except "hired" requires an offer). Any open application
can be rejected or withdrawn; a rejected one can be reopened to applied/screening.
hired and withdrawn are final. Every change is recorded in crm_application_events.
"""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, ApplicationEvent, CandidateStatus

STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected", "withdrawn"]
_ORDER = {"applied": 0, "screening": 1, "interview": 2, "offer": 3, "hired": 4}
FINAL = {"hired", "withdrawn"}

# Candidate status that follows from an application stage
CANDIDATE_STATUS_FOR_STAGE = {
    "screening": CandidateStatus.screening,
    "interview": CandidateStatus.interviewing,
    "offer": CandidateStatus.offered,
    "hired": CandidateStatus.placed,
}


def check_transition(current: str, target: str) -> str | None:
    if target not in STAGES:
        return f"Unknown stage '{target}'. Allowed: {', '.join(STAGES)}"
    if current == target:
        return f"The application is already in {target}"
    if current in FINAL:
        return f"The application is already {current} and can no longer be changed"
    if target in ("rejected", "withdrawn"):
        return None
    if current == "rejected":
        return None if target in ("applied", "screening") else "Reopen the application (move it to screening) first"
    if target == "hired" and current != "offer":
        return "A candidate can only be marked hired after an offer"
    if _ORDER.get(target, -1) > _ORDER.get(current, -1):
        return None
    return f"An application cannot move back from {current} to {target}"


def change_stage(db: AsyncSession, app: Application, target: str, actor_id: int | None,
                 note: str | None = None) -> str:
    """Validate and apply a stage change; raises 409 if not allowed. Returns the old stage."""
    current = app.stage or "applied"
    reason = check_transition(current, target)
    if reason:
        raise HTTPException(status_code=409, detail=reason)
    app.stage = target
    app.stage_changed_at = datetime.now(timezone.utc)
    db.add(ApplicationEvent(application_id=app.id, from_stage=current, to_stage=target,
                            actor_id=actor_id, note=note))
    return current
