# JobsNexGen CRM Platform

Production-grade CRM for recruitment agency operations.

## Architecture

```
crm/
├── backend/          FastAPI + PostgreSQL
│   ├── app/
│   │   ├── api/v1/   REST API routes
│   │   ├── core/     Config, DB, Security, Auth deps
│   │   ├── models/   SQLAlchemy models (24 tables)
│   │   └── services/ Email (SMTP), AI (rule-based)
│   ├── alembic/      DB migrations
│   └── .env          Environment config
└── frontend/         Next.js 14 + Tailwind
    ├── app/
    │   ├── (auth)/   Login, Forgot/Reset password
    │   └── (crm)/    Protected CRM pages
    ├── lib/api.ts    Axios API client
    └── store/auth.ts Zustand auth store
```

## Roles & Permissions

| Feature | Owner | BDM | HR |
|---------|-------|-----|----|
| Manage Team | ✓ | ✗ | ✗ |
| Create/Edit Leads | ✓ | ✓ | Own only |
| Delete Leads | ✓ | ✓ | ✗ |
| Candidates | ✓ | ✓ | ✓ |
| Analytics | ✓ | ✓ | ✓ |
| Settings | ✓ | ✓ | ✓ |

## Setup

### Backend

```bash
cd crm/backend
pip install -r requirements.txt

# Create PostgreSQL database
createdb jobsnexgen_crm

# Edit .env with your DB credentials
cp .env .env.local
# Edit DATABASE_URL and DATABASE_URL_SYNC

# Run migrations
alembic upgrade head

# Start server (port 8001)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd crm/frontend
npm install

# Edit .env.local if API URL differs
npm run dev   # runs on port 3001
```

## Production (PM2)

```bash
# Backend
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2" --name crm-api --cwd /path/to/crm/backend

# Frontend
npm run build
pm2 start "npm start" --name crm-frontend --cwd /path/to/crm/frontend
```

## Default Credentials (set up via /register endpoint)

No default admin — create first owner via the register API or direct DB insert.

## No OTP

Per requirements, there is **no OTP verification** anywhere in the system. Email/phone login only.
