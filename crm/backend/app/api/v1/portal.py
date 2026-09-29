"""
Portal integration endpoints.

Lets CRM users pull jobs / candidates / applications from the JobsNexGen job
portal into the CRM, and report on the current link status. Sync is restricted
to owner/BDM roles.
"""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_owner_or_bdm
from app.models import Candidate, CRMJob, User
from app.services import portal_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["portal-integration"])


@router.get("/status")
async def portal_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Report portal link configuration and how much data is already synced."""
    portal_jobs = (
        await db.execute(select(func.count(CRMJob.id)).where(CRMJob.portal_job_id.isnot(None)))
    ).scalar_one()
    portal_cands = (
        await db.execute(
            select(func.count(Candidate.id)).where(Candidate.portal_candidate_id.isnot(None))
        )
    ).scalar_one()

    reachable = False
    portal_job_count = None
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"{settings.PORTAL_API_URL.rstrip('/')}/stats")
            if resp.status_code == 200:
                reachable = True
                portal_job_count = resp.json().get("total_jobs")
    except Exception as e:  # noqa: BLE001
        logger.warning("Portal unreachable: %s", e)

    return {
        "portal_api_url": settings.PORTAL_API_URL,
        "portal_reachable": reachable,
        "portal_total_jobs": portal_job_count,
        "recruiter_credentials_configured": bool(
            settings.PORTAL_RECRUITER_EMAIL and settings.PORTAL_RECRUITER_PASSWORD
        ),
        "synced_jobs_in_crm": portal_jobs,
        "synced_candidates_in_crm": portal_cands,
    }


@router.post("/sync/jobs")
async def sync_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    """Pull all published portal jobs into the CRM (upsert by portal_job_id)."""
    try:
        return await portal_sync.sync_jobs(db)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Portal request failed: {e}")


@router.post("/sync/applications")
async def sync_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    """Pull recruiter applications + candidates from the portal into the CRM."""
    try:
        return await portal_sync.sync_applications(db)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Portal request failed: {e}")


@router.post("/sync/all")
async def sync_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_bdm),
):
    """Run both job and application sync in one call."""
    result = {}
    try:
        result["jobs"] = await portal_sync.sync_jobs(db)
        result["applications"] = await portal_sync.sync_applications(db)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Portal request failed: {e}")
    return result
