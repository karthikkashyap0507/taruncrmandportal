import os
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from app.auth.deps import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def ensure_upload_dir():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "resumes"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)


@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    ensure_upload_dir()
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".pdf", ".doc", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF, DOC, DOCX files are allowed")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    filename = f"{user.id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, "resumes", filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    url = f"/static/resumes/{filename}"
    return {"url": url, "filename": filename, "message": "Resume uploaded successfully"}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    ensure_upload_dir()
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, JPEG files are allowed")

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 2MB)")

    filename = f"{user.id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, "avatars", filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    url = f"/static/avatars/{filename}"
    return {"url": url, "filename": filename, "message": "Avatar uploaded successfully"}
