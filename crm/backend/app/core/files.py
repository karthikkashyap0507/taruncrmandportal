"""Private storage for candidate resumes and signed MOU documents.

Files are kept outside any public folder. The API returns short-lived signed
links only to users allowed to see a file; the download endpoint checks the
signature and expiry, so a copied or leaked link stops working.
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

KINDS = ("resumes", "agreements")
FILES_PREFIX = f"{settings.API_V1_PREFIX}/files/"
LEGACY_PREFIX = "/uploads/"
MAX_DOC_BYTES = 10 * 1024 * 1024

_SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]{1,200}")
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
DOC_EXTS = {".pdf", ".doc", ".docx"}


def private_dir(kind: str) -> str:
    path = os.path.join(settings.PRIVATE_UPLOAD_DIR, kind)
    os.makedirs(path, exist_ok=True)
    return path


def parse_file_url(url: str | None) -> tuple[str, str] | None:
    """(kind, filename) from a canonical, legacy or signed file URL; None otherwise."""
    if not url:
        return None
    path = url.split("?", 1)[0]
    for prefix in (FILES_PREFIX, LEGACY_PREFIX):
        if path.startswith(prefix):
            parts = path[len(prefix):].split("/")
            if len(parts) == 2 and parts[0] in KINDS and _SAFE_NAME.fullmatch(parts[1]):
                return parts[0], parts[1]
    return None


def canonical_url(kind: str, filename: str) -> str:
    return f"{FILES_PREFIX}{kind}/{filename}"


def _signature(kind: str, filename: str, exp: int) -> str:
    msg = f"{kind}:{filename}:{exp}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def sign_url(url: str | None) -> str | None:
    """Signed, expiring link for a stored file. Unknown or external URLs are dropped."""
    parsed = parse_file_url(url)
    if not parsed:
        return None
    kind, name = parsed
    exp = int(time.time()) + settings.SIGNED_URL_TTL_SECONDS
    return f"{FILES_PREFIX}{kind}/{name}?exp={exp}&sig={_signature(kind, name, exp)}"


def verify_signature(kind: str, filename: str, exp: int, sig: str) -> bool:
    if kind not in KINDS or exp < int(time.time()):
        return False
    return hmac.compare_digest(_signature(kind, filename, exp), sig)


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


async def save_document(file: UploadFile, kind: str, name_prefix: str) -> str:
    """Validate and store a PDF/DOC/DOCX; returns its canonical (unsigned) URL."""
    import uuid
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in DOC_EXTS:
        raise HTTPException(status_code=400, detail="Only PDF, DOC and DOCX files are allowed")
    data = await read_upload_limited(file, MAX_DOC_BYTES)
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty")
    if not content_matches(data, ext):
        raise HTTPException(status_code=400, detail=f"This file is not a valid {ext[1:].upper()} document")
    filename = f"{name_prefix}_{uuid.uuid4().hex}{ext}"
    with open(os.path.join(private_dir(kind), filename), "wb") as f:
        f.write(data)
    return canonical_url(kind, filename)
