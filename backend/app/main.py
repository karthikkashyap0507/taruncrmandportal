import json
import logging
import os
import shutil
from typing import Dict, Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.router import api_router
from app.auth.deps import resolve_user
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.files import RESUME_PREFIX, private_dir
from app.core.middleware import RequestContextMiddleware, install_error_handlers
from app.core.schema import ensure_schema
from app.models import *  # noqa: F401, F403

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, version="2.1.0", docs_url="/docs", redoc_url="/redoc")

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # Any localhost origin is only accepted while developing locally
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$" if settings.DEBUG else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_error_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            dead = set()
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_text(json.dumps(message))
                except Exception:
                    dead.add(ws)
            self.active_connections[user_id] -= dead


manager = ConnectionManager()


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str = ""):
    # Only the signed-in user may open their own channel: /ws/<id>?token=<access token>
    db = SessionLocal()
    try:
        user, _session = resolve_user(token, db)
    except HTTPException:
        await websocket.close(code=1008)
        return
    finally:
        db.close()
    if str(user.id) != user_id:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)
    try:
        await websocket.send_text(json.dumps({"type": "connected", "message": f"Connected as {user_id}"}))
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


def _migrate_legacy_data() -> None:
    """Move resumes out of the old public folder and point stored links at the
    private download endpoint; backfill job creation dates."""
    legacy = os.path.join(settings.UPLOAD_DIR, "resumes")
    target = private_dir("resumes")
    moved = 0
    if os.path.isdir(legacy):
        for name in os.listdir(legacy):
            src = os.path.join(legacy, name)
            dst = os.path.join(target, name)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.move(src, dst)
                moved += 1
    with engine.begin() as conn:
        for table in ("candidates", "applications"):
            conn.execute(
                text(f"UPDATE {table} SET resume_url = REPLACE(resume_url, '/static/resumes/', :new) "
                     "WHERE resume_url LIKE '/static/resumes/%'"),
                {"new": RESUME_PREFIX},
            )
        conn.execute(text("UPDATE jobs SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
    if moved:
        logger.info("moved %s resume(s) to private storage", moved)


@app.on_event("startup")
def on_startup():
    ensure_schema(engine, Base.metadata)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)
    private_dir("resumes")
    _migrate_legacy_data()
    from app.services.outbox import start_retry_worker
    from app.services.newsletter import start_digest_worker
    start_retry_worker()
    start_digest_worker()


# Only avatars are public. Resumes are served by /api/v1/files with signed links.
avatars_path = os.path.join(os.getcwd(), settings.UPLOAD_DIR, "avatars")
os.makedirs(avatars_path, exist_ok=True)
app.mount("/static/avatars", StaticFiles(directory=avatars_path), name="avatars")


@app.get("/health")
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok,
            "service": settings.APP_NAME, "version": "2.1.0"}
