import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.files import (
    MAX_AVATAR_BYTES,
    MAX_RESUME_BYTES,
    canonical_resume_url,
    content_matches,
    private_dir,
    read_upload_limited,
    sign_resume_url,
)
from app.core.ratelimit import upload_user_limiter
from app.models.user import User
from app.services.audit import audit

router = APIRouter(prefix="/upload", tags=["upload"])

RESUME_EXTS = {".pdf", ".doc", ".docx"}
AVATAR_EXTS = {".png", ".jpg", ".jpeg"}


@router.post("/resume")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    upload_user_limiter.check(f"u{user.id}", "Too many uploads. Please wait a few minutes.")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in RESUME_EXTS:
        raise HTTPException(status_code=400, detail="Only PDF, DOC and DOCX files are allowed")
    contents = await read_upload_limited(file, MAX_RESUME_BYTES)
    if not contents:
        raise HTTPException(status_code=400, detail="The file is empty")
    if not content_matches(contents, ext):
        raise HTTPException(status_code=400, detail=f"This file is not a valid {ext[1:].upper()} document")

    # The user id prefix ties the file to its owner; the random part makes names unguessable.
    filename = f"{user.id}_{uuid.uuid4().hex}{ext}"
    with open(os.path.join(private_dir("resumes"), filename), "wb") as f:
        f.write(contents)
    audit(db, "file.resume_uploaded", actor=user, entity_type="user", entity_id=user.id,
          details={"filename": filename, "bytes": len(contents)}, request=request, commit=True)
    return {
        "url": canonical_resume_url(filename),
        "signed_url": sign_resume_url(canonical_resume_url(filename)),
        "filename": filename,
        "message": "Resume uploaded successfully",
    }


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    upload_user_limiter.check(f"u{user.id}", "Too many uploads. Please wait a few minutes.")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in AVATAR_EXTS:
        raise HTTPException(status_code=400, detail="Only PNG, JPG and JPEG images are allowed")
    contents = await read_upload_limited(file, MAX_AVATAR_BYTES)
    if not content_matches(contents, ext):
        raise HTTPException(status_code=400, detail="This file is not a valid image")

    avatar_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)
    filename = f"{user.id}_{uuid.uuid4().hex}{ext}"
    with open(os.path.join(avatar_dir, filename), "wb") as f:
        f.write(contents)
    return {"url": f"/static/avatars/{filename}", "filename": filename, "message": "Avatar uploaded successfully"}
