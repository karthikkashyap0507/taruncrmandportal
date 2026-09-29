import paramiko, time
from pathlib import Path

HOST = '147.79.70.249'; USER = 'root'; PASS = 'Kodexatech123@'
ROOT = Path(r'C:\Users\Hii\Downloads\job portal')
FR = '/var/www/jobsnexgen/frontend'

c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=15)
sftp = c.open_sftp()

def run(cmd, t=420):
    _, o, e = c.exec_command(cmd, timeout=t)
    out = (o.read() + e.read()).decode('utf-8', 'replace')
    for l in out.strip().split('\n')[-15:]:
        sl = l.encode('ascii', 'replace').decode('ascii').strip()
        if sl: print(f'  {sl}')
    return out

print('[1] Uploading changed files...')
files = [
    ('frontend/components/shared/navbar.tsx', 'components/shared/navbar.tsx'),
    ('frontend/app/jobs/page.tsx', 'app/jobs/page.tsx'),
    ('frontend/services/api.ts', 'services/api.ts'),
]
for local, remote in files:
    sftp.put(str(ROOT / local), f'{FR}/{remote}')
    print(f'  + {remote}')

print('\n[2] Rebuild...')
run(f'cd {FR} && npm run build 2>&1', t=420)

print('\n[3] Restart frontend...')
run('pm2 restart jobsnexgen-web --update-env')
time.sleep(8)
run('pm2 list')

print('\n[4] Verify...')
run('curl -so /dev/null -w "Site: %{http_code}\n" https://jobsnexgen.com')
run('curl -so /dev/null -w "API jobs (no auth): %{http_code}\n" https://jobsnexgen.com/api/v1/jobs')

sftp.close(); c.close()
print('\nDone! Resume Builder now candidate-only. Jobs visible to all visitors.')
