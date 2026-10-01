"""Download endpoint for private documents (resumes, signed MOUs): signed links only."""
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.files import KINDS, private_dir, verify_signature

router = APIRouter(prefix="/files", tags=["files"])

_MEDIA = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/{kind}/{filename}")
def download(kind: str, filename: str, exp: int = 0, sig: str = ""):
    name = os.path.basename(filename)
    if kind not in KINDS or name != filename or not sig or not verify_signature(kind, name, exp, sig):
        raise HTTPException(403, "This link has expired or is invalid. Reload the page to get a new one.")
    path = os.path.join(private_dir(kind), name)
    if not os.path.isfile(path):
        raise HTTPException(404, "File not found")
    ext = os.path.splitext(name)[1].lower()
    return FileResponse(path, media_type=_MEDIA.get(ext, "application/octet-stream"), headers={
        "Content-Disposition": f'inline; filename="{kind[:-1]}{ext}"',
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    })
