from fastapi import APIRouter

from app.api.v1 import auth, chatbot, jobs, profiles, stats
from app.api.v1 import saved_jobs, external_jobs, upload, admin, messages, files, contact

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(profiles.router)
api_router.include_router(chatbot.router)
api_router.include_router(stats.router)
api_router.include_router(saved_jobs.router)
api_router.include_router(external_jobs.router)
api_router.include_router(upload.router)
api_router.include_router(admin.router)
api_router.include_router(messages.router)
api_router.include_router(files.router)
api_router.include_router(contact.router)
