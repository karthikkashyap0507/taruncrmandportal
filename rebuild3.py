"""Upload all fixes and rebuild"""
import paramiko, time
from pathlib import Path

HOST = "147.79.70.249"; USER = "root"; PASS = "Kodexatech123@"
PROJECT_ROOT = Path(r"C:\Users\Hii\Downloads\job portal")
FRONTEND_REMOTE = "/var/www/jobsnexgen/frontend"

def connect():
    c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=30); return c

def run(client, cmd, timeout=400):
    print(f"  $ {cmd[:90].encode('ascii','replace').decode('ascii')}")
    _, out, err = client.exec_command(cmd, timeout=timeout)
    o = out.read().decode('utf-8','replace'); e = err.read().decode('utf-8','replace')
    for line in (o+e).strip().split('\n')[-20:]:
        sl = line.encode('ascii','replace').decode('ascii').strip()
        if sl: print(f"    {sl}")
    return o

client = connect(); sftp = client.open_sftp()

files = [
    ("frontend/app/dashboard/recruiter/page.tsx", "app/dashboard/recruiter/page.tsx"),
    ("frontend/app/auth/signin/page.tsx", "app/auth/signin/page.tsx"),
]
print("[1] Uploading fixes...")
for local_rel, remote_rel in files:
    sftp.put(str(PROJECT_ROOT / local_rel), f"{FRONTEND_REMOTE}/{remote_rel}")
    print(f"  OK: {remote_rel}")

print("\n[2] Rebuild (~2min)...")
out = run(client, f"cd {FRONTEND_REMOTE} && npm run build 2>&1", timeout=420)

if "Type error" in out or "Failed to" in out:
    # Extract just the error
    lines = out.split('\n')
    for i, l in enumerate(lines):
        if 'Type error' in l or 'error TS' in l:
            for ll in lines[max(0,i-1):i+8]:
                print(f"  ERR: {ll.encode('ascii','replace').decode('ascii')}")
    print("\nBuild failed - more fixes needed")
else:
    print("\n[3] Restarting frontend...")
    run(client, "pm2 restart jobsnexgen-web --update-env")
    time.sleep(10)
    run(client, "pm2 list")
    print("\n[4] Final health check...")
    run(client, "curl -so /dev/null -w 'API: %{http_code}' http://127.0.0.1:8000/api/v1/stats && echo")
    run(client, "curl -so /dev/null -w 'Frontend: %{http_code}' http://127.0.0.1:3000 && echo")
    run(client, "curl -so /dev/null -w 'HTTPS: %{http_code}' https://jobsnexgen.com && echo")
    print("\n=== SITE IS LIVE: https://jobsnexgen.com ===")

sftp.close(); client.close()
