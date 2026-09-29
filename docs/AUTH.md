# Authentication (JobsNexGen)

## What works today

| Feature | Status |
|---------|--------|
| Email + password **register** (candidate, recruiter, company admin) | Live — recruiter/admin require **company name**; creates `Company` + `Recruiter` rows |
| Email + password **login** | Live — returns JWT access + refresh tokens and user profile |
| **Refresh token** | Live — `POST /api/v1/auth/refresh` |
| **Current user** | Live — `GET /api/v1/auth/me` (Bearer access token) |
| **Forgot / reset password** | Live — token stored in DB; with `DEBUG=true` API returns `reset_token` in JSON for local testing |
| **OAuth** (Google, GitHub, LinkedIn) | UI present — needs OAuth client IDs and redirect handlers (not wired) |
| **OTP verification** | Not implemented — add SMS/email provider when ready |
| **Platform admin** | No self-serve signup — run `python -m scripts.seed_platform_admin` |

## Run the API

**PostgreSQL not installed?** Use SQLite for local dev (default in `backend/.env.example`):

```env
DATABASE_URL=sqlite:///./jobsnexgen.db
```

The database file is created in the `backend/` folder when you start the API.

For production or Docker, use PostgreSQL.

```bash
cd backend
pip install -r requirements.txt
# Ensure PostgreSQL is running and DATABASE_URL is correct
uvicorn app.main:app --reload
```

## Frontend env

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Local password reset (dev)

1. Set `DEBUG=true` in `backend/.env`.
2. Call `POST /api/v1/auth/forgot-password` with `{ "email": "..." }`.
3. Copy `reset_token` from the JSON response.
4. Open `/auth/reset-password?token=...` on the site and set a new password.

## Production checklist

- Set strong `SECRET_KEY`, `DEBUG=false`, real `DATABASE_URL`.
- Configure SMTP (or transactional email) and remove `reset_token` from forgot-password responses.
- Add OAuth apps and callback routes.
- Rate-limit `/auth/login`, `/auth/register`, `/auth/forgot-password`.
- HTTPS only; secure cookies if you move tokens to httpOnly cookies.
