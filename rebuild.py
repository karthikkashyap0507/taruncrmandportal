"""Upload fixed files + rebuild Next.js on server"""
import paramiko
from pathlib import Path

HOST = "147.79.70.249"
USER = "root"
PASS = "Kodexatech123@"
PROJECT_ROOT = Path(r"C:\Users\Hii\Downloads\job portal")
FRONTEND_REMOTE = "/var/www/jobsnexgen/frontend"

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)
    return client

def run(client, cmd, timeout=300):
    safe = cmd[:120].encode('ascii', 'replace').decode('ascii')
    print(f"  $ {safe}")
    _, out, err = client.exec_command(cmd, timeout=timeout)
    out_text = out.read().decode('utf-8', errors='replace')
    err_text = err.read().decode('utf-8', errors='replace')
    combined = (out_text + err_text).strip()
    for line in combined.split('\n')[-20:]:
        safe_line = line.encode('ascii', 'replace').decode('ascii')
        if safe_line.strip():
            print(f"    {safe_line}")
    return out_text

def upload_file(sftp, local: Path, remote: str):
    print(f"  Uploading {local.name}...")
    sftp.put(str(local), remote)

client = connect()
sftp = client.open_sftp()

print("[1] Uploading fixed frontend files...")
# Upload all changed app files
for local_file in [
    PROJECT_ROOT / "frontend/app/ats/page.tsx",
    PROJECT_ROOT / "frontend/components/shared/apply-dialog.tsx",
    PROJECT_ROOT / "frontend/components/shared/job-card.tsx",
    PROJECT_ROOT / "frontend/components/shared/chatbot.tsx",
    PROJECT_ROOT / "frontend/app/resume-builder/page.tsx",
    PROJECT_ROOT / "frontend/app/jobs/page.tsx",
    PROJECT_ROOT / "frontend/app/dashboard/candidate/page.tsx",
    PROJECT_ROOT / "frontend/app/dashboard/recruiter/page.tsx",
    PROJECT_ROOT / "frontend/services/api.ts",
    PROJECT_ROOT / "frontend/types/index.ts",
]:
    remote_rel = str(local_file).replace(str(PROJECT_ROOT / "frontend"), "").replace("\\", "/")
    remote_path = FRONTEND_REMOTE + remote_rel
    # Ensure directory exists
    try:
        sftp.mkdir("/".join(remote_path.split("/")[:-1]))
    except Exception:
        pass
    upload_file(sftp, local_file, remote_path)

print("\n[2] Rebuilding Next.js...")
run(client, f"cd {FRONTEND_REMOTE} && npm run build 2>&1", timeout=300)

print("\n[3] Restarting frontend service...")
run(client, "pm2 restart jobsnexgen-web --update-env")
run(client, "pm2 list")

print("\n[4] Checking both services are healthy...")
import time; time.sleep(5)
run(client, "pm2 list")
run(client, "curl -s http://127.0.0.1:8000/health | head -c 100")
run(client, "curl -s http://127.0.0.1:3000 | head -c 200 | tr -d '\\n'")

sftp.close()
client.close()
print("\n[DONE] https://jobsnexgen.com is live!")
