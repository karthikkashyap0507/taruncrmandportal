"""Audit trail helper: record who did what, to which record, from where."""
from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def audit(
    db: Session,
    action: str,
    *,
    actor=None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
    request: Request | None = None,
    commit: bool = False,
) -> None:
    db.add(AuditLog(
        actor_user_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", None),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=(request.client.host if request and request.client else None),
    ))
    if commit:
        db.commit()
