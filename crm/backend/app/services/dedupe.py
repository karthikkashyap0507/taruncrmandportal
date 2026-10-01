"""Duplicate-candidate detection shared by the API and the portal sync."""
import re

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Candidate


def normalize_phone(phone: str | None) -> str | None:
    """Digits only, last 10 (so +91 98765-43210 and 9876543210 match)."""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return None
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_email(email: str | None) -> str | None:
    email = (email or "").strip().lower()
    return email or None


async def find_duplicates(db: AsyncSession, email: str | None, phone: str | None,
                          exclude_id: int | None = None) -> list[Candidate]:
    conds = []
    email = normalize_email(email)
    phone_n = normalize_phone(phone)
    if email:
        conds.append(func.lower(Candidate.email) == email)
    if phone_n:
        conds.append(Candidate.phone_normalized == phone_n)
    if not conds:
        return []
    q = select(Candidate).where(or_(*conds))
    if exclude_id:
        q = q.where(Candidate.id != exclude_id)
    return list((await db.execute(q.order_by(Candidate.id))).scalars().all())
