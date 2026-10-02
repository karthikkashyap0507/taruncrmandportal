#!/usr/bin/env python3
"""Checks the public website the way a search engine sees it (no JavaScript).

Starts the portal API on a throwaway database with one live job, builds and starts
the website against it, then checks: /jobs lists the job in its HTML, job pages
have a title and JobPosting data, robots.txt, sitemap.xml (valid XML with job URLs),
and separate Privacy Policy / Terms of Service pages linked from the footer.

Run from the repo root:  backend/venv/Scripts/python qa/frontend_check.py
Writes qa/frontend_results.md. Needs Node (npx) and the frontend's node_modules.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

import httpx

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_PORT, WEB_PORT = 8110, 3110
API = f"http://127.0.0.1:{API_PORT}/api/v1"
WEB = f"http://127.0.0.1:{WEB_PORT}"
TMP = tempfile.mkdtemp(prefix="jng-fe-", dir=os.environ.get("QA_TMP"))
NPX = "npx.cmd" if os.name == "nt" else "npx"
RESULTS = []


def py(app_dir):
    for rel in (("venv", "Scripts", "python.exe"), ("venv", "bin", "python")):
        p = os.path.join(app_dir, *rel)
        if os.path.exists(p):
            return p
    return sys.executable


def wait(url, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if httpx.get(url, timeout=3).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError(f"{url} did not come up")


def check(item, title, fn):
    try:
        RESULTS.append((item, title, "PASS", fn()))
    except Exception as exc:  # record and continue
        RESULTS.append((item, title, "FAIL", f"{type(exc).__name__}: {exc}"))
    print(f"  [{RESULTS[-1][2]}] {item} {title} :: {RESULTS[-1][3]}")


def main():
    backend = os.path.join(ROOT, "backend")
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{os.path.join(TMP, 'fe.db')}".replace("\\", "/"),
           "SECRET_KEY": "fe-check-secret-0123456789abcdef", "EMAIL_BACKEND": "console", "INTEGRATION_KEY": "",
           "UPLOAD_DIR": os.path.join(TMP, "up"), "PRIVATE_UPLOAD_DIR": os.path.join(TMP, "priv"), "DEBUG": "true",
           "CORS_ORIGINS": WEB}
    procs = []
    try:
        api_log = open(os.path.join(TMP, "api.log"), "w")
        procs.append(subprocess.Popen([py(backend), "-m", "uvicorn", "app.main:app", "--port", str(API_PORT)],
                                      cwd=backend, env=env, stdout=api_log, stderr=subprocess.STDOUT))
        wait(f"http://127.0.0.1:{API_PORT}/health")
        subprocess.run([py(backend), "-m", "scripts.seed_platform_admin"], cwd=backend, check=True, capture_output=True,
                       env={**env, "ADMIN_EMAIL": "fe-admin@qamail.in", "ADMIN_PASSWORD": "FeAdmin123!", "ADMIN_NAME": "FE Admin"})
        tok = httpx.post(f"{API}/auth/login", json={"email": "fe-admin@qamail.in", "password": "FeAdmin123!"}).json()["access_token"]
        job = httpx.post(f"{API}/jobs", headers={"Authorization": f"Bearer {tok}"}, json={
            "title": "Warehouse Supervisor SSRCHECK", "description": "Lead a team of pickers and packers on day shift.",
            "location": "Bengaluru", "locality": "Hoskote", "education": "12th", "salary_min": 22000,
            "salary_max": 28000, "salary_period": "month", "employment_type": "full_time"}).json()
        assert job["status"] == "published", job

        web_env = {**os.environ, "NEXT_PUBLIC_API_URL": API, "NEXT_PUBLIC_SITE_URL": WEB, "API_INTERNAL_URL": API}
        fe = os.path.join(ROOT, "frontend")
        print("building the website (about a minute)...")
        subprocess.run([NPX, "next", "build"], cwd=fe, env=web_env, check=True, capture_output=True)
        web_log = open(os.path.join(TMP, "web.log"), "w")
        procs.append(subprocess.Popen([NPX, "next", "start", "-p", str(WEB_PORT), "-H", "127.0.0.1"], cwd=fe,
                                      env=web_env, stdout=web_log, stderr=subprocess.STDOUT))
        wait(f"{WEB}/robots.txt")
        get = lambda path: httpx.get(f"{WEB}{path}", timeout=30)  # noqa: E731

        def jobs_page():
            r = get("/jobs")
            assert r.status_code == 200 and "Warehouse Supervisor SSRCHECK" in r.text, r.status_code
            assert "25+ verified jobs" not in r.text
            return "the HTML sent for /jobs already lists the live job (visible without JavaScript)"
        check("1", "/jobs shows real jobs", jobs_page)

        def job_page():
            r = get(f"/jobs/{job['id']}")
            assert r.status_code == 200, r.status_code
            assert "<title>Warehouse Supervisor SSRCHECK" in r.text, "title missing"
            assert '"@type":"JobPosting"' in r.text and '"unitText":"MONTH"' in r.text, "JobPosting data missing"
            return "job page has the job title in <title> and Google JobPosting data with monthly pay"
        check("1b", "Job pages are readable by search engines", job_page)

        def robots():
            r = get("/robots.txt")
            body = r.text
            assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain"), r.status_code
            assert "User-Agent: *" in body and "Allow: /" in body and "Disallow: /dashboard/" in body, body
            assert f"Sitemap: {WEB}/sitemap.xml" in body, body
            return "200 text/plain; allows public pages, blocks dashboards/API/sign-in, points to the sitemap"
        check("8", "robots.txt", robots)

        def sitemap():
            r = get("/sitemap.xml")
            assert r.status_code == 200 and "xml" in r.headers["content-type"], r.status_code
            root = ET.fromstring(r.content)
            locs = [e.text for e in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
            assert f"{WEB}/jobs/{job['id']}" in locs, locs
            assert f"{WEB}/privacy" in locs and f"{WEB}/terms" in locs, locs
            assert not any("/auth/" in loc for loc in locs), locs
            return f"200, valid XML, {len(locs)} URLs including the live job page /jobs/{job['id']}, /privacy and /terms"
        check("9", "sitemap.xml", sitemap)

        def legal():
            p, t, home = get("/privacy"), get("/terms"), get("/")
            assert p.status_code == 200 and t.status_code == 200, (p.status_code, t.status_code)
            assert "Privacy Policy" in p.text and "Digital Personal Data Protection" in p.text
            assert "Terms of Service" in t.text and "Employers and freelance recruiters" in t.text
            assert p.text != t.text
            assert 'href="/privacy"' in home.text and 'href="/terms"' in home.text, "footer links missing"
            return "/privacy and /terms are separate pages (both 200, different content) and the footer links to each"
        check("10", "Privacy Policy and Terms of Service", legal)
    finally:
        for proc in procs:
            if os.name == "nt":  # npx starts node as a child process; stop the whole tree
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
        lines = ["# Website checks (as a search engine sees it)", "",
                 f"{sum(r[2] == 'PASS' for r in RESULTS)} PASS, {sum(r[2] == 'FAIL' for r in RESULTS)} FAIL.", "",
                 "| Item | Check | Result | Evidence |", "|---|---|---|---|"]
        lines += [f"| {i} | {t} | {s} | {e.replace('|', '/')} |" for i, t, s, e in RESULTS]
        with open(os.path.join(ROOT, "qa", "frontend_results.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        if os.environ.get("QA_KEEP") != "1":
            shutil.rmtree(TMP, ignore_errors=True)
    ok = all(r[2] == "PASS" for r in RESULTS)
    print(f"\n{sum(r[2] == 'PASS' for r in RESULTS)}/{len(RESULTS)} PASS -> qa/frontend_results.md")
    return 0 if ok and RESULTS else 1


if __name__ == "__main__":
    sys.exit(main())
