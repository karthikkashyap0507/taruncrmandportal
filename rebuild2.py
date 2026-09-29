"""Upload signin fix and rebuild"""
import paramiko, time
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

def run(client, cmd, timeout=360):
    safe = cmd[:100].encode('ascii','replace').decode('ascii')
    print(f"  $ {safe}")
    _, out, err = client.exec_command(cmd, timeout=timeout)
    out_text = out.read().decode('utf-8', errors='replace')
    err_text = err.read().decode('utf-8', errors='replace')
    combined = (out_text + err_text).strip()
    for line in combined.split('\n')[-25:]:
        sl = line.encode('ascii','replace').decode('ascii').strip()
        if sl: print(f"    {sl}")
    return out_text

client = connect()
sftp = client.open_sftp()

print("[1] Uploading signin fix...")
sftp.put(str(PROJECT_ROOT / "frontend/app/auth/signin/page.tsx"),
         f"{FRONTEND_REMOTE}/app/auth/signin/page.tsx")
print("  Done")

print("\n[2] Rebuilding Next.js (this takes ~2 mins)...")
out = run(client, f"cd {FRONTEND_REMOTE} && npm run build 2>&1", timeout=400)

if "Failed" in out or "error" in out.lower() and "Type error" in out:
    print("  BUILD FAILED - checking errors...")
else:
    print("\n[3] Restarting frontend service...")
    run(client, "pm2 restart jobsnexgen-web --update-env")
    time.sleep(8)
    run(client, "pm2 list")

    print("\n[4] Health checks...")
    run(client, "curl -s http://127.0.0.1:8000/api/v1/stats")
    run(client, "curl -so /dev/null -w '%{http_code}' http://127.0.0.1:3000")
    run(client, "curl -so /dev/null -w '%{http_code}' https://jobsnexgen.com")

sftp.close()
client.close()
print("\nDone! Check https://jobsnexgen.com")
