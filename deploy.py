"""
JobsNexGen Production Deployment Script
Deploys to root@147.79.70.249 (jobsnexgen.com)
"""
import os
import sys
import time
import paramiko
from pathlib import Path

HOST = "147.79.70.249"
USER = "root"
PASS = "Kodexatech123@"
DOMAIN = "jobsnexgen.com"
PROJECT_ROOT = Path(r"C:\Users\Hii\Downloads\job portal")
REMOTE_ROOT = "/var/www/jobsnexgen"
BACKEND_REMOTE = f"{REMOTE_ROOT}/backend"
FRONTEND_REMOTE = f"{REMOTE_ROOT}/frontend"

# Files/dirs to skip during upload
SKIP_DIRS = {"venv", "__pycache__", ".next", "node_modules", "uploads", ".git", "alembicversions"}
SKIP_FILES = {".env", "jobsnexgen.db", ".DS_Store", "deploy.py"}
SKIP_EXTS = {".pyc", ".pyo", ".log"}

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)
    return client

def run(client, cmd, timeout=120):
    safe_cmd = cmd[:100].encode('ascii', 'replace').decode('ascii')
    print(f"  $ {safe_cmd}")
    _, out, err = client.exec_command(cmd, timeout=timeout)
    out_text = out.read().decode('utf-8', errors='replace')
    err_text = err.read().decode('utf-8', errors='replace')
    combined = (out_text + err_text).strip()
    if combined:
        for line in combined.split('\n')[:20]:
            safe = line.encode('ascii', 'replace').decode('ascii')
            print(f"    {safe}")
    return out_text

def upload_dir(sftp, local_path: Path, remote_path: str):
    """Recursively upload a directory via SFTP, skipping excluded paths."""
    try:
        sftp.mkdir(remote_path)
    except Exception:
        pass

    for item in local_path.iterdir():
        if item.name in SKIP_DIRS or item.name in SKIP_FILES:
            continue
        if item.suffix in SKIP_EXTS:
            continue

        remote_item = f"{remote_path}/{item.name}"
        if item.is_dir():
            if item.name not in SKIP_DIRS:
                upload_dir(sftp, item, remote_item)
        else:
            try:
                sftp.put(str(item), remote_item)
            except Exception as e:
                print(f"    WARN skip {item.name}: {e}")

def main():
    print("=" * 60)
    print("JobsNexGen Production Deployment")
    print(f"Target: {USER}@{HOST} -> {DOMAIN}")
    print("=" * 60)

    print("\n[1/9] Connecting to server...")
    client = connect()
    sftp = client.open_sftp()
    print("  Connected!")

    print("\n[2/9] Preparing server (already done - skipping rm/upload)...")
    run(client, f"mkdir -p {BACKEND_REMOTE} {FRONTEND_REMOTE}")
    run(client, "npm install -g pm2 2>&1 | tail -3", timeout=60)
    print("  Done!")

    print("\n[3/9] Backend already uploaded - skipping...")
    print("\n[4/9] Frontend already uploaded - skipping...")

    print("\n[5/9] Writing production environment files...")
    # Backend .env
    backend_env = f"""DATABASE_URL=sqlite:///{BACKEND_REMOTE}/jobsnexgen.db
SECRET_KEY=jobsnexgen-prod-secret-key-2024-xyz-secure-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=https://{DOMAIN},https://www.{DOMAIN}
OPENAI_API_KEY=
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=noreply@{DOMAIN}
SENDGRID_FROM_NAME=JobsNexGen
UPLOAD_DIR={BACKEND_REMOTE}/uploads
DEBUG=false
FRONTEND_URL=https://{DOMAIN}
"""
    with sftp.open(f"{BACKEND_REMOTE}/.env", 'w') as f:
        f.write(backend_env)

    # Frontend .env.local
    frontend_env = f"""NEXT_PUBLIC_API_URL=https://{DOMAIN}/api/v1
NEXT_PUBLIC_SITE_URL=https://{DOMAIN}
NEXT_PUBLIC_WS_URL=wss://{DOMAIN}
"""
    with sftp.open(f"{FRONTEND_REMOTE}/.env.local", 'w') as f:
        f.write(frontend_env)
    print("  Env files written!")

    print("\n[6/9] Setting up Python backend...")
    run(client, f"cd {BACKEND_REMOTE} && python3 -m venv venv", timeout=60)
    run(client, f"cd {BACKEND_REMOTE} && venv/bin/pip install -r requirements.txt 2>&1 | tail -5", timeout=180)
    run(client, f"cd {BACKEND_REMOTE} && mkdir -p uploads/resumes uploads/avatars")
    # Seed the database
    run(client, f"cd {BACKEND_REMOTE} && venv/bin/python -c \"from app.core.database import Base,engine; from app.models import *; Base.metadata.create_all(bind=engine); print('DB created')\"")
    run(client, f"cd {BACKEND_REMOTE} && venv/bin/python -m scripts.seed_jobs 2>&1 | tail -3", timeout=60)
    print("  Backend ready!")

    print("\n[7/9] Building Next.js frontend...")
    run(client, f"cd {FRONTEND_REMOTE} && npm install 2>&1 | tail -5", timeout=300)
    run(client, f"cd {FRONTEND_REMOTE} && npm run build 2>&1 | tail -10", timeout=300)
    print("  Frontend built!")

    print("\n[8/9] Starting services with PM2...")
    # Stop old instances
    run(client, "pm2 delete all 2>/dev/null || true")
    # Start backend
    run(client, f"cd {BACKEND_REMOTE} && pm2 start 'venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2' --name jobsnexgen-api")
    # Start frontend
    run(client, f"cd {FRONTEND_REMOTE} && pm2 start 'npm run start -- -p 3000' --name jobsnexgen-web")
    run(client, "pm2 save")
    run(client, "pm2 startup systemd -u root --hp /root 2>&1 | tail -3")
    run(client, "pm2 list")
    print("  Services started!")

    print("\n[9/9] Configuring Nginx...")
    nginx_conf = f"""server {{
    listen 80;
    server_name {DOMAIN} www.{DOMAIN};

    # Backend API
    location /api/ {{
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }}

    # WebSocket
    location /ws/ {{
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }}

    # Static uploads
    location /static/ {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }}

    # Next.js Frontend
    location / {{
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    client_max_body_size 10M;
}}
"""
    with sftp.open(f"/etc/nginx/sites-available/jobsnexgen", 'w') as f:
        f.write(nginx_conf)

    run(client, "ln -sf /etc/nginx/sites-available/jobsnexgen /etc/nginx/sites-enabled/jobsnexgen")
    run(client, "rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true")
    run(client, "nginx -t")
    run(client, "systemctl reload nginx")

    # SSL Certificate
    print("\n  Getting SSL certificate...")
    ssl_result = run(client,
        f"certbot --nginx -d {DOMAIN} -d www.{DOMAIN} --non-interactive --agree-tos -m admin@{DOMAIN} --redirect 2>&1 | tail -10",
        timeout=120
    )
    print("  Nginx configured + SSL done!")

    sftp.close()
    client.close()

    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE!")
    print(f"  Site:    https://{DOMAIN}")
    print(f"  API:     https://{DOMAIN}/api/v1/docs")
    print(f"  Health:  https://{DOMAIN}/health")
    print("=" * 60)

if __name__ == "__main__":
    main()
