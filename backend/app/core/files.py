"""Private storage for candidate documents.

Resumes are kept outside the public /static mount. The API returns short-lived
signed links only to users allowed to see a file, and the download endpoint
checks signature and expiry, so a copied or leaked link stops working.
"""
import hashlib
import hmac
import io
import os
import re
import time
import zipfile

from fastapi import HTTPException, UploadFile

from app.core.config import settings

RESUME_PREFIX = f"{settings.API_V1_PREFIX}/files/resumes/"
LEGACY_RESUME_PREFIX = "/static/resumes/"
MAX_RESUME_BYTES = 5 * 1024 * 1024
MAX_AVATAR_BYTES = 2 * 1024 * 1024

_SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]{1,200}")
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def private_dir(kind: str) -> str:
    path = os.path.join(settings.PRIVATE_UPLOAD_DIR, kind)
    os.makedirs(path, exist_ok=True)
    return path


def resume_filename(url: str | None) -> str | None:
    """Extract the stored filename from a canonical, legacy or signed resume URL."""
    if not url:
        return None
    path = url.split("?", 1)[0]
    for prefix in (RESUME_PREFIX, LEGACY_RESUME_PREFIX):
        if path.startswith(prefix):
            name = os.path.basename(path[len(prefix):])
            return name if _SAFE_NAME.fullmatch(name) else None
    return None


def canonical_resume_url(filename: str) -> str:
    return f"{RESUME_PREFIX}{filename}"


def resume_owner_user_id(filename: str) -> int | None:
    head = filename.split("_", 1)[0]
    return int(head) if head.isdigit() else None


def _signature(filename: str, exp: int) -> str:
    msg = f"resume:{filename}:{exp}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def sign_resume_url(url: str | None) -> str | None:
    """Signed, expiring link for a stored resume. Unknown or external URLs are dropped."""
    name = resume_filename(url)
    if not name:
        return None
    exp = int(time.time()) + settings.SIGNED_URL_TTL_SECONDS
    return f"{RESUME_PREFIX}{name}?exp={exp}&sig={_signature(name, exp)}"


def verify_signature(filename: str, exp: int, sig: str) -> bool:
    if exp < int(time.time()):
        return False
    return hmac.compare_digest(_signature(filename, exp), sig)


def content_matches(data: bytes, ext: str) -> bool:
    """Check the file's real content, not just its name."""
    if ext == ".pdf":
        return data.startswith(b"%PDF-")
    if ext == ".doc":
        return data.startswith(_OLE_MAGIC)
    if ext == ".docx":
        if not data.startswith(b"PK\x03\x04"):
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                return "word/document.xml" in zf.namelist()
        except zipfile.BadZipFile:
            return False
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return data.startswith(b"\xff\xd8\xff")
    return False


async def read_upload_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload in chunks and stop as soon as it exceeds the limit."""
    chunks, total = [], 0
    while True:
        chunk = await file.read(256 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail=f"File too large (max {max_bytes // (1024 * 1024)} MB)")
        chunks.append(chunk)
    return b"".join(chunks)


def own_resume_ref(url: str | None, user_id: int) -> str | None:
    """Validate a resume reference submitted by a user: it must be a file that this
    user uploaded. Returns the canonical (unsigned) URL to store, or None if empty."""
    if not url:
        return None
    name = resume_filename(url)
    if (not name or resume_owner_user_id(name) != user_id
            or not os.path.isfile(os.path.join(private_dir("resumes"), name))):
        raise HTTPException(status_code=400, detail="Please upload your resume using the upload button")
    return canonical_resume_url(name)
