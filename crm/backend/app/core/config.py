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
    # Candidate documents and signed MOUs: private, served only via signed links
    PRIVATE_UPLOAD_DIR: str = "private_uploads"
    SIGNED_URL_TTL_SECONDS: int = 1800

    # Email delivery: "smtp" sends for real; "console" only logs (local dev and tests)
    EMAIL_BACKEND: str = "smtp"
    EMAIL_MAX_ATTEMPTS: int = 5

    # Login protection
    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Billing defaults (used when an invoice is raised)
    GST_RATE_PERCENT: float = 18.0
    INVOICE_PREFIX: str = "JNG"

    # Background jobs (email retries, reminders); interval in seconds
    SCHEDULER_INTERVAL_SECONDS: int = 60
    SLOW_REQUEST_MS: int = 1000

    # AI (rule-based, no external API needed)
    AI_ENABLED: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
