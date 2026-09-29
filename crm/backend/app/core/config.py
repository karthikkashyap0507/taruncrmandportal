from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "JobsNexGen CRM"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "crm-super-secret-key-change-in-production-32chars+"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database (SQLite for simplicity; swap to postgresql+asyncpg:// for Postgres)
    DATABASE_URL: str = "sqlite+aiosqlite:///./crm.db"
    DATABASE_URL_SYNC: str = "sqlite:///./crm.db"

    # Redis (optional, not required for core CRM)
    REDIS_URL: str = "redis://localhost:6379/1"

    # SMTP
    SMTP_HOST: str = "smtp.hostinger.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "bdm@jobsnexgen.com"
    SMTP_PASSWORD: str = "Jobsnexgen@2026"
    FROM_NAME: str = "JobsNexGen CRM"
    FROM_EMAIL: str = "bdm@jobsnexgen.com"

    # JobsNexGen Portal Integration
    PORTAL_API_URL: str = "http://localhost:8000/api/v1"
    PORTAL_WEBHOOK_SECRET: str = "portal-webhook-secret-change-me"
    # Portal recruiter credentials used by the CRM to pull applications/candidates.
    # Leave blank to sync public jobs only (no auth required for that).
    PORTAL_RECRUITER_EMAIL: str = ""
    PORTAL_RECRUITER_PASSWORD: str = ""

    # Frontend
    FRONTEND_URL: str = "http://localhost:3001"
    CORS_ORIGINS: str = "http://localhost:3001,https://crm.jobsnexgen.com"

    # File uploads
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10

    # AI (rule-based, no external API needed)
    AI_ENABLED: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
