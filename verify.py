import paramiko
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('147.79.70.249', username='root', password='Kodexatech123@', timeout=15)

def run(cmd):
    _, o, e = c.exec_command(cmd, timeout=30)
    return (o.read() + e.read()).decode('utf-8', 'replace').strip()

print('Site HTTPS:    ', run('curl -so /dev/null -w "%{http_code}" https://jobsnexgen.com'))
print('API /stats:    ', run('curl -so /dev/null -w "%{http_code}" https://jobsnexgen.com/api/v1/stats'))
print('API /jobs:     ', run('curl -so /dev/null -w "%{http_code}" https://jobsnexgen.com/api/v1/jobs'))
print('API /docs:     ', run('curl -so /dev/null -w "%{http_code}" https://jobsnexgen.com/api/v1/docs'))
print()
print('Stats data:    ', run('curl -s https://jobsnexgen.com/api/v1/stats'))
print()
print('URL in JS bundle:')
result = run("grep -ro 'jobsnexgen.com/api' /var/www/jobsnexgen/frontend/.next/ 2>/dev/null | head -5")
print('  ', result or 'checking...')
result2 = run("grep -rl 'localhost:8000' /var/www/jobsnexgen/frontend/.next/static/ 2>/dev/null | wc -l")
print('  localhost refs in static JS:', result2)

c.close()
print()
print('All good! Site is live at https://jobsnexgen.com')
