"""Upload all current fixes and rebuild"""
import paramiko, time
from pathlib import Path

HOST = "147.79.70.249"; USER = "root"; PASS = "Kodexatech123@"
PROJECT_ROOT = Path(r"C:\Users\Hii\Downloads\job portal")
FRONTEND_REMOTE = "/var/www/jobsnexgen/frontend"

def connect():
    c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=30); return c

def run(client, cmd, timeout=420):
    print(f"  $ {cmd[:90].encode('ascii','replace').decode('ascii')}")
    _, out, err = client.exec_command(cmd, timeout=timeout)
    o = out.read().decode('utf-8','replace'); e = err.read().decode('utf-8','replace')
    combined = (o + e).strip()
    for line in combined.split('\n')[-25:]:
        sl = line.encode('ascii','replace').decode('ascii').strip()
        if sl: print(f"    {sl}")
    return o + e

client = connect(); sftp = client.open_sftp()

files = [
    "frontend/app/dashboard/recruiter/page.tsx",
    "frontend/app/auth/signin/page.tsx",
    "frontend/components/home/featured-companies.tsx",
    "frontend/app/ats/page.tsx",
    "frontend/types/index.ts",
]
print("[1] Uploading all fixes...")
for f in files:
    remote = FRONTEND_REMOTE + "/" + f.replace("frontend/", "")
    sftp.put(str(PROJECT_ROOT / f), remote)
    print(f"  OK {f.split('/')[-1]}")

print("\n[2] Build...")
out = run(client, f"cd {FRONTEND_REMOTE} && npm run build 2>&1", timeout=420)

if "Type error" in out or "Failed to" in out:
    lines = out.split('\n')
    for i, l in enumerate(lines):
        if 'Type error' in l or 'error TS' in l:
            for ll in lines[max(0,i-2):i+10]:
                print(f"  | {ll.encode('ascii','replace').decode('ascii')}")
    print("\nSTILL FAILING")
else:
    print("\n[3] Restart + health check...")
    run(client, "pm2 restart jobsnexgen-web --update-env")
    time.sleep(10)
    run(client, "pm2 list")
    run(client, "curl -so /dev/null -w 'API:%{http_code} ' http://127.0.0.1:8000/api/v1/stats && echo")
    run(client, "curl -so /dev/null -w 'Web:%{http_code} ' http://127.0.0.1:3000 && echo")
    run(client, "curl -so /dev/null -w 'HTTPS:%{http_code}' https://jobsnexgen.com && echo")
    print("\n=== https://jobsnexgen.com IS LIVE ===")

sftp.close(); client.close()
