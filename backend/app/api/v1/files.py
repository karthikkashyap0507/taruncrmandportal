"""Download endpoint for private candidate documents (signed links only)."""
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.files import private_dir, resume_filename, verify_signature, RESUME_PREFIX

router = APIRouter(prefix="/files", tags=["files"])

_MEDIA = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/resumes/{filename}")
def download_resume(filename: str, exp: int = 0, sig: str = ""):
    name = resume_filename(f"{RESUME_PREFIX}{filename}")
    if not name or not sig or not verify_signature(name, exp, sig):
        raise HTTPException(status_code=403, detail="This link has expired or is invalid. Reload the page to get a new one.")
    path = os.path.join(private_dir("resumes"), name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    ext = os.path.splitext(name)[1].lower()
    return FileResponse(
        path,
        media_type=_MEDIA.get(ext, "application/octet-stream"),
        headers={
            "Content-Disposition": f'inline; filename="resume{ext}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
