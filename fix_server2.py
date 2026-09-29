import paramiko, time

HOST = '147.79.70.249'; USER = 'root'; PASS = 'Kodexatech123@'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=15)

def run(cmd, t=60):
    _, o, e = c.exec_command(cmd, timeout=t)
    out = (o.read() + e.read()).decode('utf-8', 'replace')
    for l in out.strip().split('\n')[:20]:
        sl = l.encode('ascii', 'replace').decode('ascii').strip()
        if sl:
            print(f'  {sl}')
    return out

# Write startup script
startup_script = """#!/bin/bash
cd /var/www/jobsnexgen/backend
exec venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
"""
sftp = c.open_sftp()
with sftp.open('/var/www/jobsnexgen/backend/start.sh', 'w') as f:
    f.write(startup_script)
sftp.close()

run('chmod +x /var/www/jobsnexgen/backend/start.sh')

print('=== Killing docker on port 8000 (again if needed) ===')
run('fuser -k 8000/tcp 2>/dev/null; sleep 1; echo ok')

print('\n=== Restart API with shell script ===')
run('pm2 delete jobsnexgen-api 2>/dev/null; sleep 1; echo cleared')
run('pm2 start /var/www/jobsnexgen/backend/start.sh --name jobsnexgen-api')
time.sleep(6)

print('\n=== Backend health check ===')
run('curl -s http://127.0.0.1:8000/health')
run('curl -s http://127.0.0.1:8000/api/v1/stats | head -c 200')

print('\n=== PM2 list ===')
run('pm2 list')
run('pm2 save')

print('\n=== Nginx reload ===')
run('systemctl reload nginx')

print('\n=== Live tests ===')
run('curl -s -o /dev/null -w "HTTPS: %{http_code}\n" https://jobsnexgen.com')
run('curl -s -o /dev/null -w "API: %{http_code}\n" https://jobsnexgen.com/api/v1/stats')
run('curl -s https://jobsnexgen.com/api/v1/stats | head -c 200')

c.close()
print('Done!')
