"""
JobsNexGen CRM Deployment Script
Deploys CRM to root@147.79.70.249 under crm.jobsnexgen.com
Backend  -> port 8001 @ /var/www/jobsnexgen/crm-backend
Frontend -> port 3001 @ /var/www/jobsnexgen/crm-frontend
"""
import os
import sys
import time
import paramiko
from pathlib import Path

HOST = "147.79.70.249"
USER = "root"
PASS = "Kodexatech123@"
DOMAIN = "crm.jobsnexgen.com"
CRM_ROOT = Path(__file__).parent          # .../job portal/crm/
REMOTE_ROOT = "/var/www/jobsnexgen"
CRM_BACKEND_REMOTE = f"{REMOTE_ROOT}/crm-backend"
CRM_FRONTEND_REMOTE = f"{REMOTE_ROOT}/crm-frontend"

SKIP_DIRS  = {"venv", "__pycache__", ".next", "node_modules", "uploads", ".git", "alembic/versions"}
SKIP_FILES = {".env", "crm.db", ".env.local", ".DS_Store", "deploy.py", "README.md"}
SKIP_EXTS  = {".pyc", ".pyo", ".log", ".db"}


def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)
    return client


def run(client, cmd, timeout=180):
    safe = cmd[:120].encode("ascii", "replace").decode("ascii")
    print(f"  $ {safe}")
    _, out, err = client.exec_command(cmd, timeout=timeout)
    out_t = out.read().decode("utf-8", errors="replace")
    err_t = err.read().decode("utf-8", errors="replace")
    combined = (out_t + err_t).strip()
    if combined:
        for line in combined.split("\n")[:25]:
            print(f"    {line.encode('ascii','replace').decode('ascii')}")
    return out_t


def upload_dir(sftp, local: Path, remote: str, depth=0):
    try:
        sftp.mkdir(remote)
    except Exception:
        pass
    for item in sorted(local.iterdir()):
        if item.name in SKIP_DIRS or item.name in SKIP_FILES:
            continue
        if item.suffix in SKIP_EXTS:
            continue
        rpath = f"{remote}/{item.name}"
        if item.is_dir():
            upload_dir(sftp, item, rpath, depth + 1)
        else:
            try:
                sftp.put(str(item), rpath)
                if depth == 0:
                    print(f"    ^ {item.name}")
            except Exception as e:
                print(f"    WARN skip {item.name}: {e}")


def main():
    print("=" * 60)
    print("JobsNexGen CRM Deployment")
    print(f"Target: {USER}@{HOST}  ->  https://{DOMAIN}")
    print("=" * 60)

    print("\n[1/8] Connecting...")
    client = connect()
    sftp = client.open_sftp()
    print("  Connected!")

    # ── Prepare dirs ──────────────────────────────────────────────
    print("\n[2/8] Preparing remote directories...")
    run(client, f"mkdir -p {CRM_BACKEND_REMOTE} {CRM_FRONTEND_REMOTE}")
    run(client, f"mkdir -p {CRM_BACKEND_REMOTE}/uploads/resumes {CRM_BACKEND_REMOTE}/uploads/avatars")
    print("  Done!")

    # ── Upload backend ────────────────────────────────────────────
    print("\n[3/8] Uploading CRM backend...")
    upload_dir(sftp, CRM_ROOT / "backend", CRM_BACKEND_REMOTE)
    print("  Uploaded!")

    # ── Upload frontend ───────────────────────────────────────────
    print("\n[4/8] Uploading CRM frontend...")
    upload_dir(sftp, CRM_ROOT / "frontend", CRM_FRONTEND_REMOTE)
    print("  Uploaded!")

    # ── Write production env files ────────────────────────────────
    print("\n[5/8] Writing production env files...")
    backend_env = f"""APP_NAME=JobsNexGen CRM
DEBUG=false
SECRET_KEY=crm-prod-secret-key-jobsnexgen-2024-zxcv-secure
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=sqlite+aiosqlite:///{CRM_BACKEND_REMOTE}/crm.db
DATABASE_URL_SYNC=sqlite:///{CRM_BACKEND_REMOTE}/crm.db
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_USER=bdm@jobsnexgen.com
SMTP_PASSWORD=Jobsnexgen@2026
FROM_NAME=JobsNexGen CRM
FROM_EMAIL=bdm@jobsnexgen.com
PORTAL_API_URL=https://jobsnexgen.com/api/v1
PORTAL_WEBHOOK_SECRET=portal-webhook-secret-jobsnexgen
FRONTEND_URL=https://{DOMAIN}
CORS_ORIGINS=https://{DOMAIN},http://localhost:3001
UPLOAD_DIR={CRM_BACKEND_REMOTE}/uploads
MAX_FILE_SIZE_MB=10
AI_ENABLED=true
"""
    with sftp.open(f"{CRM_BACKEND_REMOTE}/.env", "w") as f:
        f.write(backend_env)

    frontend_env = f"""NEXT_PUBLIC_CRM_API_URL=https://{DOMAIN}
"""
    with sftp.open(f"{CRM_FRONTEND_REMOTE}/.env.local", "w") as f:
        f.write(frontend_env)
    print("  Env files written!")

    # ── Backend setup ─────────────────────────────────────────────
    print("\n[6/8] Setting up CRM backend (venv + pip + DB init)...")
    run(client, f"cd {CRM_BACKEND_REMOTE} && python3 -m venv venv", timeout=90)
    run(client, f"cd {CRM_BACKEND_REMOTE} && venv/bin/pip install --upgrade pip -q", timeout=90)
    run(client, f"cd {CRM_BACKEND_REMOTE} && venv/bin/pip install -r requirements.txt -q 2>&1 | tail -8", timeout=300)
    # Init SQLite DB using SQLAlchemy (no alembic needed for first deploy)
    init_script = (
        "import asyncio, sys; sys.path.insert(0,'.'); "
        "from app.core.database import init_db; "
        "asyncio.run(init_db()); "
        "print('CRM DB initialized')"
    )
    run(client, f"cd {CRM_BACKEND_REMOTE} && venv/bin/python -c \"{init_script}\"", timeout=60)
    print("  Backend ready!")

    # ── Frontend build ────────────────────────────────────────────
    print("\n[7/8] Building CRM frontend...")
    run(client, f"cd {CRM_FRONTEND_REMOTE} && npm install --legacy-peer-deps 2>&1 | tail -5", timeout=300)
    run(client, f"cd {CRM_FRONTEND_REMOTE} && npm run build 2>&1 | tail -15", timeout=300)
    print("  Frontend built!")

    # ── PM2 processes ─────────────────────────────────────────────
    print("\n[8/8] Starting CRM services with PM2 + configuring Nginx...")
    run(client, "pm2 delete crm-api crm-web 2>/dev/null || true")
    run(client,
        f"cd {CRM_BACKEND_REMOTE} && "
        "pm2 start 'venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 2' "
        "--name crm-api")
    run(client,
        f"cd {CRM_FRONTEND_REMOTE} && "
        "pm2 start 'npm run start -- -p 3002' --name crm-web")
    run(client, "pm2 save")
    run(client, "pm2 list")

    # ── Nginx config for crm subdomain ────────────────────────────
    nginx_conf = f"""server {{
    listen 80;
    server_name {DOMAIN};

    location /api/ {{
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }}

    location /ws/ {{
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }}

    location /uploads/ {{
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
    }}

    location / {{
        proxy_pass http://127.0.0.1:3002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    client_max_body_size 15M;
}}
"""
    with sftp.open("/etc/nginx/sites-available/jobsnexgen-crm", "w") as f:
        f.write(nginx_conf)

    run(client, "ln -sf /etc/nginx/sites-available/jobsnexgen-crm /etc/nginx/sites-enabled/jobsnexgen-crm")
    run(client, "nginx -t && systemctl reload nginx")

    # SSL for crm subdomain
    print("  Getting SSL for crm subdomain...")
    run(client,
        f"certbot --nginx -d {DOMAIN} --non-interactive --agree-tos "
        f"-m admin@jobsnexgen.com --redirect 2>&1 | tail -10",
        timeout=120)

    sftp.close()
    client.close()

    print("\n" + "=" * 60)
    print("CRM DEPLOYMENT COMPLETE!")
    print(f"  CRM Site:  https://{DOMAIN}")
    print(f"  API Docs:  https://{DOMAIN}/api/v1/docs")
    print(f"  Health:    https://{DOMAIN}/health")
    print("=" * 60)


if __name__ == "__main__":
    main()
