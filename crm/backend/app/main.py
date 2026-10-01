import asyncio
import json
import logging
import os
import shutil
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from app.api.v1 import (
    agreements, analytics, audit, auth, candidates, clients, files, incentives, invoices, jobs, leads,
    notifications, placements, portal, reports, tasks, users,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db, sync_engine
from app.core.files import FILES_PREFIX, private_dir
from app.core.middleware import RequestContextMiddleware, install_error_handlers
from app.core.security import decode_token
from app.models import Candidate, User, UserSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


# ── WebSocket connection manager ───────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        if user_id in self.active:
            self.active[user_id] = [w for w in self.active[user_id] if w != ws]

    async def send_to_user(self, user_id: int, message: dict):
        for ws in self.active.get(user_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


def _migrate_legacy_data() -> None:
    """Move resumes out of the old public folder and point stored links at the
    private download endpoint; normalise stored emails/phones for duplicate checks."""
    from app.services.dedupe import normalize_phone
    legacy = os.path.join(settings.UPLOAD_DIR, "resumes")
    target = private_dir("resumes")
    moved = 0
    if os.path.isdir(legacy):
        for name in os.listdir(legacy):
            src, dst = os.path.join(legacy, name), os.path.join(target, name)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.move(src, dst)
                moved += 1
    with sync_engine.begin() as conn:
        conn.execute(text("UPDATE crm_candidates SET resume_url = REPLACE(resume_url, '/uploads/resumes/', :p) "
                          "WHERE resume_url LIKE '/uploads/resumes/%'"), {"p": f"{FILES_PREFIX}resumes/"})
        conn.execute(text("UPDATE crm_candidates SET email = LOWER(TRIM(email)) WHERE email IS NOT NULL"))
        rows = conn.execute(text("SELECT id, phone FROM crm_candidates WHERE phone IS NOT NULL "
                                 "AND phone_normalized IS NULL")).all()
        for cid, phone in rows:
            conn.execute(text("UPDATE crm_candidates SET phone_normalized = :n WHERE id = :i"),
                         {"n": normalize_phone(phone), "i": cid})
    if moved:
        logger.info("moved %s resume(s) to private storage", moved)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting JobsNexGen CRM API...")
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)
    private_dir("resumes")
    private_dir("agreements")
    await init_db()
    await asyncio.to_thread(_migrate_legacy_data)
    from app.services.billing import seed_incentive_rules
    async with AsyncSessionLocal() as db:
        await seed_incentive_rules(db)
    from app.services.scheduler import scheduler_loop
    task = asyncio.create_task(scheduler_loop())
    logger.info("Database ready; scheduler started.")
    yield
    task.cancel()
    logger.info("Shutting down CRM API.")


app = FastAPI(
    title="JobsNexGen CRM API",
    version="1.1.0",
    description="CRM platform for the JobsNexGen recruitment agency",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_error_handlers(app)

# Only avatars are public; resumes and MOUs are served by /api/v1/files with signed links
_avatars = os.path.join(settings.UPLOAD_DIR, "avatars")
os.makedirs(_avatars, exist_ok=True)
app.mount("/uploads/avatars", StaticFiles(directory=_avatars), name="avatars")

prefix = settings.API_V1_PREFIX
for module in (auth, users, leads, clients, candidates, jobs, analytics, tasks, notifications, portal,
               agreements, placements, invoices, incentives, audit, reports, files):
    app.include_router(module.router, prefix=prefix)


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, token: str = ""):
    # Only the signed-in user may open their own channel: /ws/<id>?token=<access token>
    data = decode_token(token)
    ok = bool(data and data.get("type") == "access" and str(data.get("sub")) == str(user_id) and data.get("sid"))
    if ok:
        async with AsyncSessionLocal() as db:
            session = await db.get(UserSession, int(data["sid"]))
            user = await db.get(User, user_id)
            ok = bool(session and session.is_active and user and user.is_active)
    if not ok:
        await websocket.close(code=1008)
        return
    await manager.connect(user_id, websocket)
    try:
        while True:
            msg = json.loads(await websocket.receive_text())
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, ValueError):
        manager.disconnect(user_id, websocket)


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    db_ok = True
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "service": "JobsNexGen CRM",
            "version": "1.1.0"}


@app.get("/")
async def root():
    return {"message": "JobsNexGen CRM API"}
