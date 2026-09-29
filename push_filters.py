import paramiko, time
from pathlib import Path

HOST = '147.79.70.249'; USER = 'root'; PASS = 'Kodexatech123@'
ROOT = Path(r'C:\Users\Hii\Downloads\job portal')
FR = '/var/www/jobsnexgen/frontend'
BE = '/var/www/jobsnexgen/backend'

c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=15)
sftp = c.open_sftp()

def run(cmd, t=420):
    _, o, e = c.exec_command(cmd, timeout=t)
    out = (o.read() + e.read()).decode('utf-8', 'replace')
    for l in out.strip().split('\n')[-12:]:
        sl = l.encode('ascii', 'replace').decode('ascii').strip()
        if sl: print(f'  {sl}')
    return out

print('[1] Upload files...')
sftp.put(str(ROOT / 'frontend/app/jobs/page.tsx'), f'{FR}/app/jobs/page.tsx')
sftp.put(str(ROOT / 'backend/app/api/v1/jobs.py'), f'{BE}/app/api/v1/jobs.py')
print('  done')

print('\n[2] Rebuild frontend...')
run(f'cd {FR} && npm run build 2>&1', t=420)

print('\n[3] Restart services...')
run('pm2 restart jobsnexgen-web --update-env')
run('pm2 restart jobsnexgen-api --update-env')
time.sleep(8)
run('pm2 list')

print('\n[4] Health check...')
run('curl -so /dev/null -w "Site: %{http_code}\n" https://jobsnexgen.com')
run('curl -so /dev/null -w "API: %{http_code}\n" https://jobsnexgen.com/api/v1/jobs?limit=5')

sftp.close(); c.close()
print('\nDone! New filters live at https://jobsnexgen.com/jobs')
