from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "JobsNexGen API"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production-use-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = "sqlite:///./jobsnexgen.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: str = "http://localhost:3000"
    OPENAI_API_KEY: str = ""
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@jobsnexgen.in"
    SENDGRID_FROM_NAME: str = "JobsNexGen"
    UPLOAD_DIR: str = "uploads"
    # Resumes live here, outside the public /static mount; they are only served
    # through short-lived signed links (see app/core/files.py).
    PRIVATE_UPLOAD_DIR: str = "private_uploads"
    SIGNED_URL_TTL_SECONDS: int = 1800
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:3000"

    # Email delivery: "smtp" sends for real; "console" only logs (local dev and tests).
    EMAIL_BACKEND: str = "smtp"
    EMAIL_MAX_ATTEMPTS: int = 5
    # Contact-form enquiries are emailed here (a mailbox the SMTP account can deliver to)
    CONTACT_INBOX: str = "bdm@jobsnexgen.com"

    # Login protection
    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Requests slower than this are logged as warnings
    SLOW_REQUEST_MS: int = 1000

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
