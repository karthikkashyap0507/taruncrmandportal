import json
import os
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.models import *  # noqa: F401, F403

app = FastAPI(title=settings.APP_NAME, version="1.0.0", docs_url="/docs", redoc_url="/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
async def websocket_endpoint(websocket: WebSocket, user_id: str):
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


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # Ensure upload directories exist
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "resumes"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)
    # Add new columns to existing SQLite DB (idempotent migrations)
    from sqlalchemy import text
    with engine.connect() as conn:
        for col, col_type in [
            ("full_name", "VARCHAR(255)"),
            ("phone", "VARCHAR(50)"),
            ("years_experience", "INTEGER"),
            ("cover_letter", "TEXT"),
            ("resume_url", "VARCHAR(500)"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE applications ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                pass  # Column already exists


# Serve uploaded files as static
uploads_path = os.path.join(os.getcwd(), settings.UPLOAD_DIR)
os.makedirs(uploads_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=uploads_path), name="static")


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": "2.0.0"}
