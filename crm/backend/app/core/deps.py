from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token, utc
from app.models import User, UserRole, UserSession

bearer = HTTPBearer(auto_error=False)

SESSION_ENDED = "Your session has ended. Please sign in again."


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = decode_token(credentials.credentials)
    if not data or data.get("type") != "access" or "sub" not in data or "sid" not in data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        user_id, session_id = int(data["sub"]), int(data["sid"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    now = datetime.now(timezone.utc)
    session = await db.get(UserSession, session_id)
    if not session or session.user_id != user_id or not session.is_active or utc(session.expires_at) < now:
        raise HTTPException(status_code=401, detail=SESSION_ENDED)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    if not session.last_used_at or utc(session.last_used_at) < now - timedelta(minutes=5):
        session.last_used_at = now
        await db.commit()
    request.state.session_id = session_id
    return user


def require_roles(*roles: UserRole):
    async def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You don't have permission to do this")
        return user
    return check


require_owner = require_roles(UserRole.owner)
require_owner_or_bdm = require_roles(UserRole.owner, UserRole.bdm)
require_any = get_current_user


def is_owner(user: User) -> bool:
    return user.role == UserRole.owner
