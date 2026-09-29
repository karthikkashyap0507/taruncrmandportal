import paramiko, time

HOST = '147.79.70.249'; USER = 'root'; PASS = 'Kodexatech123@'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=15)
sftp = c.open_sftp()

def run(cmd, t=360):
    _, o, e = c.exec_command(cmd, timeout=t)
    out = (o.read() + e.read()).decode('utf-8', 'replace')
    for l in out.strip().split('\n')[-20:]:
        sl = l.encode('ascii', 'replace').decode('ascii').strip()
        if sl: print(f'  {sl}')
    return out

print('=== Current env files on server ===')
run('cat /var/www/jobsnexgen/frontend/.env 2>/dev/null || echo "no .env"')
run('cat /var/www/jobsnexgen/frontend/.env.local 2>/dev/null || echo "no .env.local"')

print('\n=== Overwriting ALL env files with production URLs ===')
prod_env = """NEXT_PUBLIC_API_URL=https://jobsnexgen.com/api/v1
NEXT_PUBLIC_SITE_URL=https://jobsnexgen.com
NEXT_PUBLIC_WS_URL=wss://jobsnexgen.com
"""
# Write to both .env and .env.local to be sure
for fname in ['.env', '.env.local', '.env.production', '.env.production.local']:
    with sftp.open(f'/var/www/jobsnexgen/frontend/{fname}', 'w') as f:
        f.write(prod_env)
    print(f'  Wrote {fname}')

print('\n=== Rebuilding Next.js with correct URLs ===')
run('cd /var/www/jobsnexgen/frontend && npm run build 2>&1', t=420)

print('\n=== Restarting frontend ===')
run('pm2 restart jobsnexgen-web --update-env')
time.sleep(8)
run('pm2 list')

print('\n=== Verify env baked into build ===')
run('grep -r "localhost:8000" /var/www/jobsnexgen/frontend/.next/server/ 2>/dev/null | wc -l || echo "0 localhost refs in build"')

print('\nDone! All API calls now go to https://jobsnexgen.com/api/v1')
sftp.close(); c.close()
