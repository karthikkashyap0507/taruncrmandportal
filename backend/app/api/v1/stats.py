from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application import Application, ApplicationStatus
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.job import Job, JobStatus

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    """Public stats for the home page hero section (real counts only)."""
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return {
        "total_jobs": db.query(Job).filter(Job.status == JobStatus.published).count(),
        "total_companies": db.query(Company).count(),
        "total_candidates": db.query(Candidate).count(),
        "total_applications": db.query(Application).count(),
        "placements_this_month": db.query(Application).filter(
            Application.status == ApplicationStatus.hired,
            Application.status_changed_at >= month_start,
        ).count(),
    }
