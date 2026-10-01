from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token_safe, utc
from app.core.database import get_db
from app.models.session import UserSession
from app.models.user import User, UserRole

security = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


def resolve_user(token: str, db: Session) -> tuple[User, UserSession]:
    """Validate an access token against its session. Raises 401/403 on failure."""
    payload = decode_token_safe(token)
    if not payload or payload.get("type") != "access" or "sub" not in payload or "sid" not in payload:
        raise _unauthorized("Invalid or expired token")
    try:
        user_id, session_id = int(payload["sub"]), int(payload["sid"])
    except (TypeError, ValueError):
        raise _unauthorized("Invalid token")

    now = datetime.now(timezone.utc)
    session = db.get(UserSession, session_id)
    if (not session or session.user_id != user_id or session.revoked_at is not None
            or utc(session.expires_at) < now):
        raise _unauthorized("Your session has ended. Please sign in again.")

    user = db.get(User, user_id)
    if not user:
        raise _unauthorized("User not found")
    if user.is_active is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been deactivated.")

    # Record activity at most every 5 minutes, not on every request
    if not session.last_used_at or utc(session.last_used_at) < now - timedelta(minutes=5):
        session.last_used_at = now
        db.commit()
    return user, session


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Session = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Not authenticated")
    user, session = resolve_user(credentials.credentials, db)
    request.state.session_id = session.id
    return user


def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Session = Depends(get_db),
) -> User | None:
    """The signed-in user if a valid token was sent, otherwise None (for public endpoints)."""
    if not credentials:
        return None
    try:
        user, session = resolve_user(credentials.credentials, db)
    except HTTPException:
        return None
    request.state.session_id = session.id
    return user


def require_roles(*roles: UserRole):
    def _inner(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _inner
