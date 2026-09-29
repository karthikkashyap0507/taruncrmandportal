from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os, logging, json
from typing import Dict, List

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import auth, users, leads, clients, candidates, jobs, analytics, tasks, notifications, portal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
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

    async def broadcast(self, message: dict):
        for connections in self.active.values():
            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting JobsNexGen CRM API...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "resumes"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)
    try:
        await init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"DB init failed: {e}")
    yield
    logger.info("Shutting down CRM API.")


app = FastAPI(
    title="JobsNexGen CRM API",
    version="1.0.0",
    description="Production-grade CRM platform for JobsNexGen recruitment agency",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# API Routers
prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)
app.include_router(leads.router, prefix=prefix)
app.include_router(clients.router, prefix=prefix)
app.include_router(candidates.router, prefix=prefix)
app.include_router(jobs.router, prefix=prefix)
app.include_router(analytics.router, prefix=prefix)
app.include_router(tasks.router, prefix=prefix)
app.include_router(notifications.router, prefix=prefix)
app.include_router(portal.router, prefix=prefix)


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    logger.info(f"WS connected: user {user_id}")
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        logger.info(f"WS disconnected: user {user_id}")


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "JobsNexGen CRM", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "JobsNexGen CRM API", "docs": "/docs"}
