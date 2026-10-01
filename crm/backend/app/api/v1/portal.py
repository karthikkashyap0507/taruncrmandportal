"""
Job portal integration.

Portal jobs and applications flow into the CRM automatically (see
services/portal_sync.py). These endpoints show the link's health and let
owners/BDMs run a sync straight away instead of waiting for the next one.
"""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_owner_or_bdm
from app.models import ActivityType, User
from app.services import portal_sync
from app.services.activity import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["portal-integration"])


@router.get("/status")
async def portal_status(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """When the last sync ran, whether it worked, and how much portal data is in the CRM."""
    return await portal_sync.status(db)


async def _sync(db: AsyncSession, user: User, request: Request, full: bool) -> dict:
    if not portal_sync.configured():
        raise HTTPException(status_code=503, detail="Portal sync is not set up: PORTAL_INTEGRATION_KEY is missing "
                                                    "on the CRM server.")
    try:
        result = await portal_sync.run_sync(db, full=full)
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        reason = "the integration keys on the portal and CRM don't match" if code in (401, 403) else f"HTTP {code}"
        raise HTTPException(status_code=502, detail=f"The job portal refused the sync: {reason}.")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Couldn't reach the job portal: {e}")
    log_activity(db, user, ActivityType.update, "Synced jobs and applicants from the job portal", "portal", None,
                 changes={k: v for k, v in result.items() if isinstance(v, int) and v}, request=request)
    await db.commit()
    return result


@router.post("/sync")
async def sync_now(request: Request, full: bool = False, db: AsyncSession = Depends(get_db),
                   current_user: User = Depends(require_owner_or_bdm)):
    """Pull new and changed portal jobs and applications now. full=true re-reads everything."""
    return await _sync(db, current_user, request, full)


# Older paths kept so existing bookmarks/scripts keep working; all run the same sync.
@router.post("/sync/jobs", include_in_schema=False)
@router.post("/sync/applications", include_in_schema=False)
@router.post("/sync/all", include_in_schema=False)
async def sync_legacy(request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(require_owner_or_bdm)):
    return await _sync(db, current_user, request, False)
