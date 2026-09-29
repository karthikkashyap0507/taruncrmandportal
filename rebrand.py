"""
Rebrand JobsNexGen — replace old blue-purple palette with brand blue-orange-green
Logo colours: #1B75BB (blue) · #F7941D (orange) · #39B54A (green)
"""
import paramiko, time
from pathlib import Path

HOST = '147.79.70.249'; USER = 'root'; PASS = 'Kodexatech123@'
ROOT = Path(r'C:\Users\Hii\Downloads\job portal')
FR = '/var/www/jobsnexgen/frontend'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=20)
sftp = c.open_sftp()

def run(cmd, t=420):
    _, o, e = c.exec_command(cmd, timeout=t)
    out = (o.read() + e.read()).decode('utf-8', 'replace')
    for l in out.strip().split('\n')[-15:]:
        sl = l.encode('ascii', 'replace').decode('ascii').strip()
        if sl: print(f'  {sl}')
    return out

# ── 1. Upload changed source files ───────────────────────────────────────────
print('[1] Upload globals.css + navbar...')
sftp.put(str(ROOT / 'frontend/app/globals.css'), f'{FR}/app/globals.css')
sftp.put(str(ROOT / 'frontend/components/shared/navbar.tsx'), f'{FR}/components/shared/navbar.tsx')
print('  done')

# ── 2. Bulk sed replace on the server ────────────────────────────────────────
print('\n[2] Bulk colour replace across all .tsx/.ts files...')

# Map: old_color → new_color (case-insensitive hex values)
REPLACEMENTS = [
    # Purple → Orange  (most important: #8B5CF6, #8b5cf6, 8B5CF6)
    ('#8B5CF6', '#F7941D'),
    ('#8b5cf6', '#f7941d'),
    ('8B5CF6',  'F7941D'),
    # Cyan → Green  (#06B6D4)
    ('#06B6D4', '#39B54A'),
    ('#06b6d4', '#39b54a'),
    ('06B6D4',  '39B54A'),
    # Emerald → Brand Green  (#10B981)
    ('#10B981', '#39B54A'),
    ('#10b981', '#39b54a'),
    ('10B981',  '39B54A'),
    # Blue → Brand Blue  (#3B82F6)
    ('#3B82F6', '#1B75BB'),
    ('#3b82f6', '#1b75bb'),
    ('3B82F6',  '1B75BB'),
    # rgba versions
    ('rgba(59, 130, 246',  'rgba(27, 117, 187'),
    ('rgba(139, 92, 246',  'rgba(247, 148, 29'),
    ('rgba(6, 182, 212',   'rgba(57, 181, 74'),
    ('rgba(16, 185, 129',  'rgba(57, 181, 74'),
    # Background darkening
    ('#0F172A', '#091626'),
    ('#0f172a', '#091626'),
    ('#111827', '#0F1F35'),
    ('#111827', '#0F1F35'),
    # Dark card
    ('bg-\\[#111827\\]', 'bg-[#0F1F35]'),
]

# Build a combined sed command (safer to do one at a time)
sed_parts = []
for old, new in REPLACEMENTS:
    # Escape special chars for sed
    old_esc = old.replace('/', '\\/').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')
    new_esc = new.replace('/', '\\/').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')
    sed_parts.append(f"s/{old_esc}/{new_esc}/g")

sed_cmd = '; '.join(sed_parts)

# Run on all .tsx and .ts files (excluding node_modules and .next)
find_cmd = (
    f"find {FR}/app {FR}/components {FR}/services {FR}/lib {FR}/store {FR}/types "
    f"-name '*.tsx' -o -name '*.ts' | "
    f"xargs sed -i '{sed_cmd}' 2>/dev/null; echo 'replaced'"
)
run(find_cmd, t=60)

# Also update the jobs page we already changed locally
sftp.put(str(ROOT / 'frontend/app/jobs/page.tsx'), f'{FR}/app/jobs/page.tsx')

# ── 3. Rebuild ────────────────────────────────────────────────────────────────
print('\n[3] Rebuild frontend (~2 min)...')
run(f'cd {FR} && npm run build 2>&1', t=420)

# ── 4. Restart ────────────────────────────────────────────────────────────────
print('\n[4] Restart frontend...')
run('pm2 restart jobsnexgen-web --update-env')
time.sleep(10)
run('pm2 list')

# ── 5. Verify ─────────────────────────────────────────────────────────────────
print('\n[5] Final check...')
run('curl -so /dev/null -w "Site: %{http_code}\n" https://jobsnexgen.com')

sftp.close(); c.close()
print('\nRebranding complete! https://jobsnexgen.com')
