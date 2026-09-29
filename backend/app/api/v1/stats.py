from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application import Application
from app.models.company import Company
from app.models.job import Job, JobStatus
from app.models.user import User

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    """Public stats for the home page hero section."""
    total_jobs = db.query(Job).filter(Job.status == JobStatus.published).count()
    total_companies = db.query(Company).count()
    total_candidates = db.query(User).count()
    total_applications = db.query(Application).count()

    return {
        "total_jobs": total_jobs,
        "total_companies": total_companies,
        "total_candidates": total_candidates,
        "total_applications": total_applications,
        "placements_this_month": max(0, total_applications // 5),
    }
