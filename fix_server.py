import paramiko, time

HOST = '147.79.70.249'; USER = 'root'; PASS = 'Kodexatech123@'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=15)

def run(cmd, t=60):
    _, o, e = c.exec_command(cmd, timeout=t)
    out = (o.read() + e.read()).decode('utf-8', 'replace')
    for l in out.strip().split('\n')[:15]:
        sl = l.encode('ascii', 'replace').decode('ascii').strip()
        if sl:
            print(f'  {sl}')
    return out

print('=== What is on port 8000? ===')
run('lsof -i :8000 | head -5')

print('\n=== Kill port 8000 squatter ===')
run('fuser -k 8000/tcp 2>/dev/null || true; sleep 2; echo killed')
run('pkill -f uvicorn 2>/dev/null; pkill -f gunicorn 2>/dev/null; sleep 2; echo done')

print('\n=== Stop and delete all PM2 processes ===')
run('pm2 delete all 2>/dev/null; sleep 1; echo cleared')

print('\n=== Verify port is free ===')
run('ss -tlnp | grep 8000 || echo "port 8000 is free"')

print('\n=== Start backend with PM2 (single worker) ===')
run('pm2 start /var/www/jobsnexgen/backend/venv/bin/uvicorn --name jobsnexgen-api -- app.main:app --host 127.0.0.1 --port 8000')
time.sleep(6)

print('\n=== Test backend health ===')
run('curl -s http://127.0.0.1:8000/health')

print('\n=== Start frontend ===')
run('pm2 start npm --name jobsnexgen-web --cwd /var/www/jobsnexgen/frontend -- run start -- -p 3000')
time.sleep(8)

print('\n=== PM2 final list ===')
run('pm2 list')
run('pm2 save')

print('\n=== Final checks ===')
run('curl -s http://127.0.0.1:8000/api/v1/stats')
run('curl -s -o /dev/null -w "Site: %{http_code}" https://jobsnexgen.com')
run('curl -s -o /dev/null -w "  API: %{http_code}" https://jobsnexgen.com/api/v1/stats')

c.close()
print('\nDone!')
