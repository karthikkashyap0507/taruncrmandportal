# JobsNexGen

Next Generation AI-Powered Hiring Platform — production-ready monorepo with Next.js frontend and FastAPI backend.

## Stack

- **Frontend:** Next.js 16, TypeScript, Tailwind CSS, ShadCN UI, Framer Motion, React Query, Zustand
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, Redis, JWT auth
- **Infra:** Docker Compose

## Quick Start

### Frontend only

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Full stack (Docker)

```bash
docker compose up --build
```

### Backend only (local)

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env
# Default .env uses SQLite — no PostgreSQL needed for local dev
uvicorn app.main:app --reload
```

Use PostgreSQL in production (`DATABASE_URL=postgresql://...`). For Docker: `docker compose up`.

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Authentication

JWT auth is wired end-to-end. See **[docs/AUTH.md](docs/AUTH.md)** for register/login/refresh/me, password reset, and platform-admin seeding.

**Frontend:** create `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` so sign-in calls your API.

**Recruiter / company admin signup:** enter a **company name** on the register form. The API creates a `Company` and `Recruiter` row (this was required for recruiter signup to succeed).

## Pages

| Route | Description |
|-------|-------------|
| `/` | Home — hero, trending jobs, AI showcase, FAQ |
| `/jobs` | Job search with filters |
| `/about` | About Us |
| `/services` | Add On Services |
| `/contact` | Contact form + map |
| `/auth/signin` | Sign in / Register (API-backed) |
| `/auth/reset-password` | New password with reset token |
| `/dashboard/candidate` | Candidate dashboard (after login) |
| `/dashboard/recruiter` | Recruiter dashboard |
| `/dashboard/company` | Company admin dashboard |
| `/dashboard/admin` | Platform admin (seed script only) |

## Project Structure

```
job portal/
├── frontend/          # Next.js app
├── backend/           # FastAPI app
├── docker-compose.yml
└── README.md
```

## Environment

Copy `frontend/.env.example` and `backend/.env.example` to `.env` and adjust values.

## Next Steps

- OAuth (Google, GitHub, LinkedIn) with real client IDs and callbacks
- Email/SMS OTP verification
- Elasticsearch + Qdrant for semantic search
- OpenAI resume parsing and AI matching
- Full dashboard modules (ATS, analytics, billing)
- WebSockets for real-time notifications
