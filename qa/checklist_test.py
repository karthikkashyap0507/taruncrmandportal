#!/usr/bin/env python3
"""JobsNexGen QA checklist suite.

Starts the job portal API and the CRM API on throwaway databases (real email is
never sent), then exercises every item of the client checklist through the real
HTTP API and records PASS/FAIL with evidence.

Run from the repo root with the portal's virtualenv (it has httpx, jose, websockets):
    backend/venv/Scripts/python qa/checklist_test.py        (Windows)
    backend/venv/bin/python qa/checklist_test.py            (Linux/macOS)
Writes qa/results.json and qa/results.md.
"""
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
import uuid

import httpx
from jose import jwt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PORTAL_DIR = os.path.join(ROOT, "backend")
CRM_DIR = os.path.join(ROOT, "crm", "backend")
PORTAL_PORT, CRM_PORT = 8100, 8101
SECRET = "qa-secret-key-0123456789abcdef0123456789abcdef"
TMP = tempfile.mkdtemp(prefix="jng-qa-", dir=os.environ.get("QA_TMP"))
PORTAL_DB = os.path.join(TMP, "portal.db").replace("\\", "/")
CRM_DB = os.path.join(TMP, "crm.db").replace("\\", "/")

RESULTS: list[dict] = []


def venv_python(app_dir: str) -> str:
    for rel in (("venv", "Scripts", "python.exe"), ("venv", "bin", "python")):
        p = os.path.join(app_dir, *rel)
        if os.path.exists(p):
            return p
    return sys.executable


# ── result recording ──────────────────────────────────────────────────────────

def record(section: str, item: str, title: str, passed: bool, evidence: str) -> None:
    RESULTS.append({"section": section, "item": item, "title": title,
                    "status": "PASS" if passed else "FAIL", "evidence": evidence})
    print(f"  [{'PASS' if passed else 'FAIL'}] {item} {title} :: {evidence}")


def run_check(section: str, item: str, title: str, fn) -> None:
    try:
        evidence = fn()
        record(section, item, title, True, evidence or "ok")
    except AssertionError as exc:
        record(section, item, title, False, str(exc) or "assertion failed")
    except Exception as exc:  # unexpected error: record it, keep going
        record(section, item, title, False, f"{type(exc).__name__}: {exc}")
        traceback.print_exc()


def expect(resp: httpx.Response, *codes: int) -> httpx.Response:
    assert resp.status_code in codes, f"{resp.request.method} {resp.request.url.path} -> {resp.status_code} " \
                                      f"(expected {codes}): {resp.text[:200]}"
    return resp


# ── servers ───────────────────────────────────────────────────────────────────

class Server:
    def __init__(self, name, app_dir, port, env):
        self.name, self.app_dir, self.port, self.env = name, app_dir, port, env
        self.proc = None

    def start(self, **overrides):
        env = {**os.environ, **self.env, **overrides}
        log = open(os.path.join(TMP, f"{self.name}.log"), "a")
        self.proc = subprocess.Popen(
            [venv_python(self.app_dir), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(self.port)], cwd=self.app_dir, env=env, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(120):
            try:
                if httpx.get(f"http://127.0.0.1:{self.port}/health", timeout=2).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        raise RuntimeError(f"{self.name} did not start; see {TMP}/{self.name}.log")

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


portal = Server("portal", PORTAL_DIR, PORTAL_PORT, {
    "DATABASE_URL": f"sqlite:///{PORTAL_DB}",
    "UPLOAD_DIR": os.path.join(TMP, "portal_up"), "PRIVATE_UPLOAD_DIR": os.path.join(TMP, "portal_priv"),
    "SECRET_KEY": SECRET, "DEBUG": "true", "CORS_ORIGINS": "http://localhost", "INTEGRATION_KEY": "",
})
crm = Server("crm", CRM_DIR, CRM_PORT, {
    "DATABASE_URL": f"sqlite+aiosqlite:///{CRM_DB}", "DATABASE_URL_SYNC": f"sqlite:///{CRM_DB}",
    "UPLOAD_DIR": os.path.join(TMP, "crm_up"), "PRIVATE_UPLOAD_DIR": os.path.join(TMP, "crm_priv"),
    "SECRET_KEY": SECRET, "DEBUG": "false", "SCHEDULER_INTERVAL_SECONDS": "3",
    "PORTAL_API_URL": f"http://127.0.0.1:{PORTAL_PORT}/api/v1", "CORS_ORIGINS": "http://localhost",
    "PORTAL_INTEGRATION_KEY": "",
})

# Phase C: fresh databases with the portal -> CRM link switched on
QA_INTEGRATION_KEY = "qa-integration-key-0123456789"
SYNC_PORTAL_DB = os.path.join(TMP, "portal_sync.db").replace("\\", "/")
SYNC_CRM_DB = os.path.join(TMP, "crm_sync.db").replace("\\", "/")
portal_sync_srv = Server("portal_sync", PORTAL_DIR, PORTAL_PORT, {
    **portal.env, "DATABASE_URL": f"sqlite:///{SYNC_PORTAL_DB}", "INTEGRATION_KEY": QA_INTEGRATION_KEY,
    "UPLOAD_DIR": os.path.join(TMP, "portal2_up"), "PRIVATE_UPLOAD_DIR": os.path.join(TMP, "portal2_priv"),
})
crm_sync_srv = Server("crm_sync", CRM_DIR, CRM_PORT, {
    **crm.env, "DATABASE_URL": f"sqlite+aiosqlite:///{SYNC_CRM_DB}", "DATABASE_URL_SYNC": f"sqlite:///{SYNC_CRM_DB}",
    "PORTAL_INTEGRATION_KEY": QA_INTEGRATION_KEY, "PORTAL_SYNC_INTERVAL_SECONDS": "3",
    "UPLOAD_DIR": os.path.join(TMP, "crm2_up"), "PRIVATE_UPLOAD_DIR": os.path.join(TMP, "crm2_priv"),
})

P = lambda path: f"http://127.0.0.1:{PORTAL_PORT}/api/v1{path}"  # noqa: E731
C = lambda path: f"http://127.0.0.1:{CRM_PORT}/api/v1{path}"     # noqa: E731
http = httpx.Client(timeout=30)
_ip_counter = [0]


def fresh_ip() -> str:
    """Each caller gets its own client IP (via the trusted proxy header) so rate limits don't collide."""
    _ip_counter[0] += 1
    n = _ip_counter[0]
    return f"10.{(n // 65536) % 256}.{(n // 256) % 256}.{n % 256}"


def H(token=None, ip=None) -> dict:
    h = {}
    if token:
        h["Authorization"] = f"Bearer {token}"
    h["X-Forwarded-For"] = ip or fresh_ip()
    return h


def db_rows(path, sql, args=()):
    con = sqlite3.connect(path)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def wait_for(predicate, timeout=15, step=0.5):
    end = time.time() + timeout
    while time.time() < end:
        v = predicate()
        if v:
            return v
        time.sleep(step)
    return predicate()


def claims(token: str) -> dict:
    return jwt.get_unverified_claims(token)


# ── portal helpers ────────────────────────────────────────────────────────────

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def p_register(name, email, role="candidate", company=None, password="QaTest123!"):
    body = {"name": name, "email": email, "password": password, "role": role}
    if company:
        body["company_name"] = company
    return expect(http.post(P("/auth/register"), json=body, headers=H()), 201).json()


def p_login(email, password="QaTest123!", ip=None):
    return http.post(P("/auth/login"), json={"email": email, "password": password}, headers=H(ip=ip))


def seed_portal_admin(email, password, server=None):
    env = {**os.environ, **(server or portal).env, "ADMIN_EMAIL": email, "ADMIN_PASSWORD": password, "ADMIN_NAME": "QA Admin"}
    subprocess.run([venv_python(PORTAL_DIR), "-m", "scripts.seed_platform_admin"], cwd=PORTAL_DIR, env=env,
                   check=True, capture_output=True)


def post_live_job(S, token, body):
    """Post a job as an employer and approve it as the platform admin (employer jobs start as pending)."""
    job = expect(http.post(P("/jobs"), json=body, headers=H(token)), 201).json()
    if job["status"] == "pending":
        expect(http.post(P(f"/admin/jobs/{job['id']}/approve"), headers=H(S["admin"])), 200)
        job["status"] = "published"
    return job


# ── crm helpers ───────────────────────────────────────────────────────────────

def c_login(credential, password="CrmTest123!", ip=None):
    return http.post(C("/auth/login"), json={"credential": credential, "password": password}, headers=H(ip=ip))


def c_token(credential, password="CrmTest123!"):
    return expect(c_login(credential, password), 200).json()["access_token"]


def outbox(db, table, category=None):
    sql = f"SELECT id, category, to_email, status, attempts, last_error FROM {table}"
    if category:
        return db_rows(db, sql + " WHERE category = ? ORDER BY id", (category,))
    return db_rows(db, sql + " ORDER BY id")


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE A: delivery failures are logged and retryable
# ══════════════════════════════════════════════════════════════════════════════

def phase_a():
    print("\n== Phase A: email delivery failures (EMAIL_BACKEND=fail) ==")
    portal.start(EMAIL_BACKEND="fail")
    crm.start(EMAIL_BACKEND="fail")
    seed_portal_admin("admin@qamail.in", "AdminQa123!")
    p_register("Fail Test", "failtest@qamail.in")  # welcome email -> will fail
    owner = expect(http.post(C("/auth/register"), json={"name": "QA Owner", "email": "owner@qamail.in",
                                                       "password": "CrmTest123!"}, headers=H()), 201).json()
    expect(http.post(C("/users/"), json={"name": "Fail Member", "email": "failmember@qamail.in",
                                        "password": "CrmTest123!", "role": "hr"},
                     headers=H(owner["access_token"])), 201)

    def check_logged():
        p_rows = wait_for(lambda: [r for r in outbox(PORTAL_DB, "email_outbox", "welcome") if r[3] == "failed"])
        c_rows = wait_for(lambda: [r for r in outbox(CRM_DB, "crm_email_outbox", "welcome") if r[3] == "failed"])
        assert p_rows and c_rows, f"portal={outbox(PORTAL_DB, 'email_outbox')} crm={outbox(CRM_DB, 'crm_email_outbox')}"
        assert "simulated delivery failure" in (p_rows[0][5] or ""), p_rows
        nxt = db_rows(PORTAL_DB, "SELECT next_attempt_at FROM email_outbox WHERE id=?", (p_rows[0][0],))[0][0]
        assert nxt, "no retry scheduled"
        return f"portal email #{p_rows[0][0]} status=failed error='{p_rows[0][5][:45]}...' retry scheduled at {nxt}; " \
               f"CRM email #{c_rows[0][0]} status=failed"
    run_check("Notifications", "N-6a", "Failed notifications are logged with the error and a retry time", check_logged)

    def admin_retry_while_failing():
        tok = expect(p_login("admin@qamail.in", "AdminQa123!"), 200).json()["access_token"]
        row_id = outbox(PORTAL_DB, "email_outbox", "welcome")[0][0]
        r = expect(http.post(P(f"/admin/notifications/{row_id}/retry"), headers=H(tok)), 200).json()
        assert r["status"] in ("failed", "dead"), r
        listing = expect(http.get(P("/admin/notifications?status=failed"), headers=H(tok)), 200).json()
        ctok = owner["access_token"]
        clist = expect(http.get(C("/notifications/deliveries?status=failed"), headers=H(ctok)), 200).json()
        assert listing["total"] >= 1 and clist["total"] >= 1, (listing, clist)
        return f"admin retry while SMTP is down -> still '{r['status']}' (attempt counted); failures visible to " \
               f"portal admin ({listing['total']}) and CRM owner ({clist['total']})"
    run_check("Notifications", "N-6b", "Admins can see failed emails and retry them", admin_retry_while_failing)
    portal.stop()
    crm.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE B: everything else (EMAIL_BACKEND=console)
# ══════════════════════════════════════════════════════════════════════════════

def phase_b():
    print("\n== Phase B: full checklist (EMAIL_BACKEND=console) ==")
    portal.start(EMAIL_BACKEND="console")
    crm.start(EMAIL_BACKEND="console")
    S = {}  # shared state between checks

    # N-6c: retry succeeds once delivery works again
    def retry_after_recovery():
        tok = expect(p_login("admin@qamail.in", "AdminQa123!"), 200).json()["access_token"]
        row_id = outbox(PORTAL_DB, "email_outbox", "welcome")[0][0]
        r = expect(http.post(P(f"/admin/notifications/{row_id}/retry"), headers=H(tok)), 200).json()
        assert r["status"] == "sent", r
        ctok = c_token("owner@qamail.in")
        rc = expect(http.post(C("/notifications/deliveries/retry-failed"), headers=H(ctok)), 200).json()
        assert rc["sent"] >= 1, rc
        return f"after SMTP recovered: portal email #{row_id} -> sent; CRM retry-failed sent {rc['sent']}/{rc['attempted']}"
    run_check("Notifications", "N-6c", "Failed emails are delivered when retried after recovery", retry_after_recovery)

    setup_users(S)
    login_and_sessions(S)
    p0_checks(S)
    p1_checks(S)
    notification_checks(S)
    performance_checks(S)
    p2_checks(S)
    extra_checks(S)
    portal.stop()
    crm.stop()


def setup_users(S):
    S["admin"] = expect(p_login("admin@qamail.in", "AdminQa123!"), 200).json()["access_token"]
    S["recA"] = p_register("Rec A", "reca@qamail.in", "recruiter", "Company A")["access_token"]
    S["recB"] = p_register("Rec B", "recb@qamail.in", "recruiter", "Company B")["access_token"]
    S["cand1"] = p_register("Cand One", "cand1@qamail.in")["access_token"]
    S["cand2"] = p_register("Cand Two", "cand2@qamail.in")["access_token"]
    S["owner"] = c_token("owner@qamail.in")
    for role, email in (("bdm", "bdm@qamail.in"), ("hr", "hr1@qamail.in"), ("hr", "hr2@qamail.in")):
        expect(http.post(C("/users/"), json={"name": email.split("@")[0].upper(), "email": email,
                                            "password": "CrmTest123!", "role": role}, headers=H(S["owner"])), 201)
    S["bdm"], S["hr1"], S["hr2"] = c_token("bdm@qamail.in"), c_token("hr1@qamail.in"), c_token("hr2@qamail.in")
    S["ids"] = {u["name"]: u["id"] for u in expect(http.get(C("/users/"), headers=H(S["owner"])), 200).json()}


# ── Login & session management ────────────────────────────────────────────────

def login_and_sessions(S):
    sec = "Login & Session"

    def login_logout():
        out = []
        r = p_register("Sess User", "sess@qamail.in")
        tok = r["access_token"]
        expect(http.get(P("/auth/me"), headers=H(tok)), 200)
        expect(http.post(P("/auth/logout"), headers=H(tok)), 200)
        expect(http.get(P("/auth/me"), headers=H(tok)), 401)
        expect(http.post(P("/auth/refresh"), json={"refresh_token": r["refresh_token"]}, headers=H()), 401)
        out.append("portal: token works -> logout -> same access token 401, refresh 401")
        cr = expect(c_login("hr2@qamail.in"), 200).json()
        expect(http.get(C("/auth/me"), headers=H(cr["access_token"])), 200)
        expect(http.post(C("/auth/logout"), json={"refresh_token": cr["refresh_token"]},
                         headers=H(cr["access_token"])), 200)
        expect(http.get(C("/auth/me"), headers=H(cr["access_token"])), 401)
        out.append("CRM: same (access token rejected immediately after logout)")
        return "; ".join(out)
    run_check(sec, "AUTH-1", "Login / logout (logout revokes tokens immediately)", login_logout)

    def password_reset():
        email = "reset@qamail.in"
        old = p_register("Reset User", email)
        r = expect(http.post(P("/auth/forgot-password"), json={"email": email}, headers=H()), 200).json()
        token = r.get("reset_token")
        assert token, "no token returned in DEBUG mode"
        assert wait_for(lambda: outbox(PORTAL_DB, "email_outbox", "password_reset")), "reset email not queued"
        expect(http.post(P("/auth/reset-password"), json={"token": token, "new_password": "NewPass123!"},
                         headers=H()), 200)
        expect(p_login(email, "NewPass123!"), 200)
        expect(p_login(email, "QaTest123!"), 401)
        expect(http.get(P("/auth/me"), headers=H(old["access_token"])), 401)
        expect(http.post(P("/auth/reset-password"), json={"token": token, "new_password": "Another123!"},
                         headers=H()), 400)
        # CRM
        expect(http.post(C("/auth/forgot-password"), json={"email": "hr2@qamail.in"}, headers=H()), 200)
        ctoken = db_rows(CRM_DB, "SELECT token FROM crm_password_resets WHERE email='hr2@qamail.in' "
                                 "ORDER BY id DESC LIMIT 1")[0][0]
        assert wait_for(lambda: outbox(CRM_DB, "crm_email_outbox", "password_reset")), "CRM reset email not queued"
        hr2_old = c_token("hr2@qamail.in")
        expect(http.post(C("/auth/reset-password"), json={"token": ctoken, "new_password": "CrmNew123!"},
                         headers=H()), 200)
        expect(http.get(C("/auth/me"), headers=H(hr2_old)), 401)
        S["hr2"] = c_token("hr2@qamail.in", "CrmNew123!")
        expect(http.post(C("/auth/reset-password"), json={"token": ctoken, "new_password": "X1234567!"},
                         headers=H()), 400)
        return "portal + CRM: reset email queued -> new password works, old password fails, existing " \
               "sessions revoked, reset link single-use"
    run_check(sec, "AUTH-2", "Password reset", password_reset)

    def session_expiry():
        r = p_register("Expiry User", "expiry@qamail.in")
        c = claims(r["access_token"])
        expired = jwt.encode({"sub": c["sub"], "sid": c["sid"], "type": "access",
                              "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)}, SECRET, "HS256")
        expect(http.get(P("/auth/me"), headers=H(expired)), 401)
        con = sqlite3.connect(PORTAL_DB)
        con.execute("UPDATE user_sessions SET expires_at='2020-01-01 00:00:00' WHERE id=?", (c["sid"],))
        con.commit()
        con.close()
        expect(http.post(P("/auth/refresh"), json={"refresh_token": r["refresh_token"]}, headers=H()), 401)
        cr = expect(c_login("hr1@qamail.in"), 200).json()
        cc = claims(cr["access_token"])
        cexp = jwt.encode({"sub": cc["sub"], "sid": cc["sid"], "type": "access",
                           "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)}, SECRET, "HS256")
        expect(http.get(C("/auth/me"), headers=H(cexp)), 401)
        con = sqlite3.connect(CRM_DB)
        con.execute("UPDATE crm_user_sessions SET expires_at='2020-01-01 00:00:00' WHERE id=?", (cc["sid"],))
        con.commit()
        con.close()
        expect(http.post(C("/auth/refresh"), json={"refresh_token": cr["refresh_token"]}, headers=H()), 401)
        return "expired access tokens -> 401 and expired sessions can't be refreshed (portal + CRM); " \
               "access tokens last 60 min, sessions 7 days"
    run_check(sec, "AUTH-3", "Session expiry", session_expiry)

    def multi_device():
        email = "multi@qamail.in"
        p_register("Multi Device", email)
        laptop = expect(p_login(email), 200).json()
        phone = expect(p_login(email), 200).json()
        sessions = expect(http.get(P("/auth/sessions"), headers=H(laptop["access_token"])), 200).json()
        assert len(sessions) >= 3, sessions  # register + 2 logins
        phone_sid = claims(phone["access_token"])["sid"]
        expect(http.delete(P(f"/auth/sessions/{phone_sid}"), headers=H(laptop["access_token"])), 200)
        expect(http.get(P("/auth/me"), headers=H(phone["access_token"])), 401)
        expect(http.get(P("/auth/me"), headers=H(laptop["access_token"])), 200)
        expect(http.post(P("/auth/logout-all"), headers=H(laptop["access_token"])), 200)
        expect(http.get(P("/auth/me"), headers=H(laptop["access_token"])), 401)
        # CRM: two logins in the same instant used to crash with a duplicate token
        a, b = c_login("hr1@qamail.in"), c_login("hr1@qamail.in")
        expect(a, 200), expect(b, 200)
        ta, tb = a.json()["access_token"], b.json()["access_token"]
        cs = expect(http.get(C("/auth/sessions"), headers=H(ta)), 200).json()
        expect(http.delete(C(f"/auth/sessions/{claims(tb)['sid']}"), headers=H(ta)), 200)
        expect(http.get(C("/auth/me"), headers=H(tb)), 401)
        expect(http.get(C("/auth/me"), headers=H(ta)), 200)
        return f"portal: {len(sessions)} devices listed, revoking one signs only that device out, " \
               f"logout-all ends the rest; CRM: back-to-back logins both succeed ({len(cs)} sessions), per-device revoke works"
    run_check(sec, "AUTH-4", "Multiple-device sessions", multi_device)

    def lockout_and_rate_limit():
        email = "lock@qamail.in"
        p_register("Lock User", email)
        codes = [p_login(email, f"wrong{i}").status_code for i in range(5)]
        locked = p_login(email)
        assert codes == [401] * 5 and locked.status_code == 423, (codes, locked.status_code)
        ccodes = [c_login("bdm@qamail.in", f"wrong{i}").status_code for i in range(5)]
        clocked = c_login("bdm@qamail.in")
        assert ccodes == [401] * 5 and clocked.status_code == 423, (ccodes, clocked.status_code)
        con = sqlite3.connect(CRM_DB)
        con.execute("UPDATE crm_users SET locked_until=NULL, failed_login_count=0 WHERE email='bdm@qamail.in'")
        con.commit()
        con.close()
        ip = fresh_ip()
        statuses = [p_login("nobody@qamail.in", "x", ip=ip).status_code for _ in range(25)]
        cstatuses = [c_login("nobody@qamail.in", "x", ip=ip).status_code for _ in range(25)]
        limited = http.post(P("/auth/login"), json={"email": "nobody@qamail.in", "password": "x"}, headers=H(ip=ip))
        assert 429 in statuses and 429 in cstatuses, (statuses, cstatuses)
        assert "Retry-After" in limited.headers, dict(limited.headers)
        return f"5 wrong passwords -> account locked (423) even for the right password, on both apps; " \
               f"25 rapid attempts from one IP -> 429 after {statuses.index(429)} (portal) / " \
               f"{cstatuses.index(429)} (CRM) with Retry-After"
    run_check(sec, "AUTH-5", "Account lockout / rate limiting", lockout_and_rate_limit)

    def unauthorized_dashboard():
        checks = [
            (http.get(P("/auth/me"), headers=H()), 401),
            (http.get(P("/admin/stats"), headers=H(S["cand1"])), 403),
            (http.get(P("/admin/users"), headers=H(S["recA"])), 403),
            (http.get(P("/jobs/recruiter/my"), headers=H(S["cand1"])), 403),
            (http.get(C("/users/"), headers=H(S["hr1"])), 403),
            (http.get(C("/leads/"), headers=H()), 401),
            (http.get(C("/audit-logs"), headers=H(S["bdm"])), 403),
        ]
        bad = [(r.request.url.path, r.status_code, want) for r, want in checks if r.status_code != want]
        assert not bad, bad
        guards = 0
        for d in ("admin", "candidate", "company", "recruiter"):
            src = open(os.path.join(ROOT, "frontend", "app", "dashboard", d, "page.tsx"), encoding="utf-8").read()
            guards += ("router.replace" in src and "role" in src)
        crm_layout = open(os.path.join(ROOT, "crm", "frontend", "app", "(crm)", "layout.tsx"), encoding="utf-8").read()
        assert guards == 4 and 'router.push("/login")' in crm_layout, "frontend guards missing"
        return f"{len(checks)} API probes rejected (401 without login, 403 wrong role); all 4 portal dashboards and " \
               "the CRM layout redirect unauthorised users"
    run_check(sec, "AUTH-6", "Unauthorized dashboard access", unauthorized_dashboard)


# ── P0 ────────────────────────────────────────────────────────────────────────

def p0_checks(S):
    sec = "P0"
    # Portal fixtures: job by company A, application by cand1 with resume
    job = post_live_job(S, S["recA"], {"title": "Backend Engineer", "description": "Python FastAPI SQL role",
                                       "skills": ["python", "sql"], "location": "Bangalore"})
    S["jobA"] = job["id"]
    up = expect(http.post(P("/upload/resume"), files={"file": ("cv.pdf", PDF, "application/pdf")},
                          headers=H(S["cand1"])), 200).json()
    S["cand1_resume"] = up["url"]
    ap = expect(http.post(P(f"/jobs/{S['jobA']}/apply"), json={"full_name": "Cand One", "resume_url": up["url"],
                                                               "years_experience": 3}, headers=H(S["cand1"])), 200).json()
    S["appA"] = ap["application_id"]
    expect(http.post(P(f"/messages/applications/{S['appA']}"), json={"content": "Hi from recruiter A"},
                     headers=H(S["recA"])), 201)

    def data_leakage():
        ev = []
        expect(http.get(P(f"/messages/applications/{S['appA']}"), headers=H(S["recB"])), 404)
        expect(http.get(P(f"/jobs/{S['jobA']}/applications"), headers=H(S["recB"])), 404)
        ev.append("another company's recruiter can't read the conversation or applicants (404)")
        draft = expect(http.post(P("/jobs"), json={"title": "Secret Draft", "description": "Not public yet at all",
                                                   "status": "draft"}, headers=H(S["recA"])), 201).json()
        expect(http.get(P(f"/jobs/{draft['id']}"), headers=H()), 404)
        expect(http.get(P(f"/jobs/{draft['id']}"), headers=H(S["recA"])), 200)
        ev.append("draft jobs hidden from the public")
        a = expect(http.post(P("/chatbot/message"), json={"message": "hello"}, headers=H()), 200).json()
        b = expect(http.post(P("/chatbot/message"), json={"message": "hello"}, headers=H()), 200).json()
        assert a["conversation_id"] != b["conversation_id"], "chatbot shares a conversation"
        ev.append("chatbot visitors no longer share one conversation")
        fname = S["cand1_resume"].rsplit("/", 1)[1]
        expect(http.get(f"http://127.0.0.1:{PORTAL_PORT}/static/resumes/{fname}"), 404)
        ev.append("resumes not served from public /static")
        try:
            from websockets.sync.client import connect
            rejected = False
            try:
                with connect(f"ws://127.0.0.1:{PORTAL_PORT}/ws/1", open_timeout=5) as ws:
                    ws.recv(timeout=3)
            except Exception:
                rejected = True
            assert rejected, "websocket accepted without a token"
            uid = claims(S["cand1"])["sub"]
            with connect(f"ws://127.0.0.1:{PORTAL_PORT}/ws/{uid}?token={S['cand1']}", open_timeout=5) as ws:
                assert "connected" in ws.recv(timeout=5)
            ev.append("live-notification socket refuses connections without a valid token")
        except ImportError:
            ev.append("(websocket check skipped: websockets not installed)")
        # CRM: HR can't open another person's lead / task, can't see billing
        lead = expect(http.post(C("/leads/"), json={"company_name": "Private Lead Co", "contact_name": "X",
                                                    "assigned_to_id": S["ids"]["BDM"]}, headers=H(S["bdm"])), 201).json()
        expect(http.get(C(f"/leads/{lead['id']}"), headers=H(S["hr1"])), 404)
        expect(http.get(C(f"/leads/{lead['id']}/notes"), headers=H(S["hr1"])), 404)
        task = expect(http.post(C("/tasks/"), json={"title": "BDM private task"}, headers=H(S["bdm"])), 201).json()
        expect(http.put(C(f"/tasks/{task['id']}"), json={"title": "hijack"}, headers=H(S["hr1"])), 404)
        assert all(t["id"] != task["id"] for t in expect(http.get(C("/tasks/"), headers=H(S["hr1"])), 200).json())
        expect(http.get(C("/invoices/"), headers=H(S["hr1"])), 403)
        ev.append("CRM HR users can't open others' leads/tasks by ID or see billing")
        return "; ".join(ev)
    run_check(sec, "P0-1", "Data leakage", data_leakage)

    def api_authorization():
        probes = [
            ("candidate posts a job", http.post(P("/jobs"), json={"title": "x" * 5, "description": "y" * 12},
                                                headers=H(S["cand1"])), 403),
            ("candidate changes own application status", http.patch(P(f"/jobs/applications/{S['appA']}"),
                                                                    json={"status": "offered"}, headers=H(S["cand1"])), 403),
            ("candidate sends an 'offer' message", http.post(P(f"/messages/applications/{S['appA']}"),
                                                            json={"content": "I hire myself", "message_type": "offer"},
                                                            headers=H(S["cand1"])), 403),
            ("other company's recruiter updates the application", http.patch(P(f"/jobs/applications/{S['appA']}"),
                                                                             json={"status": "rejected"}, headers=H(S["recB"])), 404),
            ("other company's recruiter edits the job", http.patch(P(f"/jobs/{S['jobA']}"), json={"title": "Hacked job"},
                                                                    headers=H(S["recB"])), 404),
            ("recruiter sets an ATS score by hand", http.patch(P(f"/jobs/applications/{S['appA']}"),
                                                              json={"score": 100}, headers=H(S["recA"])), 200),
            ("no token on a protected endpoint", http.get(P("/profiles/me"), headers=H()), 401),
            ("candidate opens CRM-style admin endpoint", http.get(P("/admin/audit-logs"), headers=H(S["cand1"])), 403),
        ]
        bad = [(name, r.status_code, want) for name, r, want in probes if r.status_code != want]
        assert not bad, bad
        score = db_rows(PORTAL_DB, "SELECT score FROM applications WHERE id=?", (S["appA"],))[0][0]
        assert score != 100, f"score was overwritten: {score}"
        return f"{len(probes)} authorization probes behave correctly; manual ATS score ignored (stays {score:.0f})"
    run_check(sec, "P0-2", "API authorization", api_authorization)

    def role_permissions():
        client = expect(http.post(C("/clients/"), json={"name": "Throwaway Client"}, headers=H(S["bdm"])), 201).json()
        cand = expect(http.post(C("/candidates/"), json={"name": "Throwaway Cand", "email": "throw@qamail.in"},
                                headers=H(S["hr1"])), 201).json()
        cjob = expect(http.post(C("/jobs/"), json={"title": "Throwaway Job"}, headers=H(S["bdm"])), 201).json()
        matrix = [
            ("GET /users (team list)", lambda t: http.get(C("/users/"), headers=H(t)), {"owner": 200, "bdm": 403, "hr1": 403}),
            ("GET /audit-logs", lambda t: http.get(C("/audit-logs"), headers=H(t)), {"owner": 200, "bdm": 403, "hr1": 403}),
            ("POST /clients", lambda t: http.post(C("/clients/"), json={"name": "C"}, headers=H(t)), {"bdm": 201, "hr1": 403}),
            ("POST /jobs", lambda t: http.post(C("/jobs/"), json={"title": "Role X"}, headers=H(t)), {"bdm": 201, "hr1": 403}),
            ("GET /analytics/revenue", lambda t: http.get(C("/analytics/revenue"), headers=H(t)), {"owner": 200, "bdm": 200, "hr1": 403}),
            ("GET /analytics/team/performance", lambda t: http.get(C("/analytics/team/performance"), headers=H(t)), {"owner": 200, "bdm": 403, "hr1": 403}),
            ("GET /agreements (MOUs)", lambda t: http.get(C("/agreements/"), headers=H(t)), {"bdm": 200, "hr1": 403}),
            ("PUT /incentives/rules/hr", lambda t: http.put(C("/incentives/rules/hr"), json={"percentage": 49}, headers=H(t)), {"bdm": 403, "hr1": 403}),
            ("GET /reports/invoices.csv", lambda t: http.get(C("/reports/invoices.csv"), headers=H(t)), {"bdm": 200, "hr1": 403}),
            ("DELETE candidate", lambda t: http.delete(C(f"/candidates/{cand['id']}"), headers=H(t)), {"hr1": 403, "bdm": 403, "owner": 200}),
            ("DELETE job", lambda t: http.delete(C(f"/jobs/{cjob['id']}"), headers=H(t)), {"hr1": 403, "bdm": 403, "owner": 200}),
            ("DELETE client", lambda t: http.delete(C(f"/clients/{client['id']}"), headers=H(t)), {"hr1": 403, "bdm": 403, "owner": 200}),
        ]
        bad, n = [], 0
        for name, call, expected in matrix:
            for role, want in expected.items():
                n += 1
                got = call(S[role]).status_code
                if got != want:
                    bad.append(f"{name} as {role}: {got} (want {want})")
        assert not bad, bad
        return f"{n} role/endpoint combinations match the permission matrix (owner / BDM / HR)"
    run_check(sec, "P0-3", "Role permissions", role_permissions)

    def document_security():
        ev = []
        fake = http.post(P("/upload/resume"), files={"file": ("cv.pdf", b"<html><script>x</script></html>",
                                                              "application/pdf")}, headers=H(S["cand1"]))
        assert fake.status_code == 400, fake.text
        big = http.post(P("/upload/resume"), files={"file": ("big.pdf", PDF + b"0" * (5 * 1024 * 1024),
                                                             "application/pdf")}, headers=H(S["cand1"]))
        assert big.status_code == 413, big.status_code
        ev.append("fake PDF rejected (400), >5 MB rejected (413)")
        apps = expect(http.get(P(f"/jobs/{S['jobA']}/applications"), headers=H(S["recA"])), 200).json()
        link = apps[0]["resume_url"]
        assert link and "sig=" in link and "exp=" in link, link
        dl = http.get(f"http://127.0.0.1:{PORTAL_PORT}{link}")
        assert dl.status_code == 200 and dl.content.startswith(b"%PDF"), dl.status_code
        bare = link.split("?")[0]
        expect(http.get(f"http://127.0.0.1:{PORTAL_PORT}{bare}"), 403)
        expect(http.get(f"http://127.0.0.1:{PORTAL_PORT}{link[:-4]}abcd"), 403)
        name = bare.rsplit("/", 1)[1]
        old_exp = int(time.time()) - 60
        sig = hmac.new(SECRET.encode(), f"resume:{name}:{old_exp}".encode(), hashlib.sha256).hexdigest()
        expect(http.get(f"http://127.0.0.1:{PORTAL_PORT}{bare}?exp={old_exp}&sig={sig}"), 403)
        ev.append("recruiter gets a signed link that works; unsigned, tampered and expired links -> 403")
        job2 = post_live_job(S, S["recA"], {"title": "QA Analyst", "description": "Testing role for QA team"})
        steal = http.post(P(f"/jobs/{job2['id']}/apply"), json={"resume_url": S["cand1_resume"]}, headers=H(S["cand2"]))
        js = http.patch(P("/profiles/candidate/me"), json={"resume_url": "javascript:alert(1)"}, headers=H(S["cand2"]))
        assert steal.status_code == 400 and js.status_code == 400, (steal.status_code, js.status_code)
        ev.append("another candidate can't attach my resume; javascript: links refused")
        cc = expect(http.post(C("/candidates/"), json={"name": "Doc Cand", "email": "doc@qamail.in"},
                              headers=H(S["hr1"])), 201).json()
        bad = http.post(C(f"/candidates/{cc['id']}/resume"), files={"file": ("a.pdf", b"MZ\x90\x00binary", "application/pdf")},
                        headers=H(S["hr1"]))
        assert bad.status_code == 400, bad.status_code
        good = expect(http.post(C(f"/candidates/{cc['id']}/resume"), files={"file": ("a.pdf", PDF, "application/pdf")},
                                headers=H(S["hr1"])), 200).json()["resume_url"]
        assert "sig=" in good
        expect(http.get(f"http://127.0.0.1:{CRM_PORT}{good}"), 200)
        expect(http.get(f"http://127.0.0.1:{CRM_PORT}{good.split('?')[0]}"), 403)
        expect(http.get(f"http://127.0.0.1:{CRM_PORT}/uploads/resumes/{good.split('?')[0].rsplit('/', 1)[1]}"), 404)
        ev.append("CRM: content-checked uploads, private storage, signed links only")
        return "; ".join(ev)
    run_check(sec, "P0-4", "Candidate document security", document_security)

    billing_setup(S)

    def incentive_manipulation():
        ev = []
        B = S["billing"]
        r = http.post(C("/incentives/"), json={"user_id": S["ids"]["HR1"], "amount": 999999}, headers=H(S["hr1"]))
        assert r.status_code in (404, 405), r.status_code
        r2 = http.put(C(f"/incentives/{B['incentive_ids'][0]}"), json={"amount": 999999}, headers=H(S["hr1"]))
        assert r2.status_code in (404, 405), r2.status_code
        ev.append("there is no API to create or edit an incentive amount (405)")
        expect(http.put(C("/incentives/rules/hr"), json={"percentage": 50}, headers=H(S["hr1"])), 403)
        expect(http.post(C(f"/incentives/{B['incentive_ids'][0]}/approve"), headers=H(S["hr1"])), 403)
        ev.append("HR can't change rates or approve their own payout (403)")
        mine = expect(http.get(C("/incentives/"), headers=H(S["hr1"])), 200).json()["data"]
        assert mine and all(i["user_id"] == S["ids"]["HR1"] for i in mine), mine
        assert B["hr_incentive_amount"] is not None and abs(B["expected_hr_incentive"] - B["hr_incentive_amount"]) < 0.01, B
        assert B["credited_people"] == sorted([S["ids"]["HR1"], S["ids"]["BDM"]]), B["credited_people"]
        ev.append(f"HR sees only their own incentives; amount = invoice {B['invoice_amount']:,.0f} x "
                  f"{B['hr_rate']}% = {B['hr_incentive_amount']:,.0f}, computed by the server for exactly the "
                  "credited recruiter and BDM")
        assert B["placement_fee_ignored_client_value"], "client-supplied fee was used"
        assert B["recruiter_forced_to_self"], "HR could credit someone else"
        ev.append("fee and credited recruiter can't be set by the client")
        assert B["bdm_override_forbidden"] and B["override_needs_reason"], "invoice override not protected"
        ev.append("invoice amount override: BDM 403, owner needs a reason (audited)")
        assert B["voided_on_cancel"] >= 1 and B["voided_on_guarantee"] >= 1, B
        ev.append(f"incentives voided when the invoice is cancelled ({B['voided_on_cancel']}) and when the "
                  f"candidate leaves within guarantee ({B['voided_on_guarantee']})")
        return "; ".join(ev)
    run_check(sec, "P0-5", "Royalty / incentive manipulation", incentive_manipulation)


def billing_setup(S):
    """Full MOU -> placement -> joining -> invoice -> incentive flow (used by P0-5 and P1-3)."""
    B = S["billing"] = {}
    o, bdm, hr1 = S["owner"], S["bdm"], S["hr1"]
    client = expect(http.post(C("/clients/"), json={"name": "Acme Corp", "industry": "IT"}, headers=H(bdm)), 201).json()
    expect(http.post(C(f"/clients/{client['id']}/contacts"), json={"company_id": client["id"], "name": "Asha Client",
                                                                   "email": "asha@acme-corp.in", "is_primary": True},
                     headers=H(bdm)), 201)
    job = expect(http.post(C("/jobs/"), json={"title": "Data Engineer", "company_id": client["id"],
                                              "assigned_to_id": S["ids"]["HR1"]}, headers=H(bdm)), 201).json()
    cand = expect(http.post(C("/candidates/"), json={"name": "Ravi Placed", "email": "ravi@qamail.in",
                                                     "phone": "+91 99887 76655"}, headers=H(hr1)), 201).json()
    app = expect(http.post(C(f"/jobs/{job['id']}/applications"), json={"candidate_id": cand["id"]}, headers=H(hr1)), 201).json()
    for stage in ("screening", "interview", "offer"):
        expect(http.patch(C(f"/jobs/{job['id']}/applications/{app['id']}/stage?stage={stage}"), headers=H(hr1)), 200)
    B.update(client=client, job=job, cand=cand, app=app)

    body = {"candidate_id": cand["id"], "job_id": job["id"], "offered_ctc": 1200000,
            "recruiter_id": S["ids"]["HR2"], "bdm_id": S["ids"]["BDM"], "fee_amount": 1,
            "expected_joining_date": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=20)).isoformat()}
    B["no_mou"] = http.post(C("/placements/"), json=body, headers=H(hr1)).status_code
    mou = expect(http.post(C("/agreements/"), json={"company_id": client["id"], "title": "Acme MSA 2026",
                                                   "fee_type": "percentage", "fee_value": 12.5, "payment_terms_days": 30,
                                                   "replacement_guarantee_days": 90,
                                                   "start_date": "2026-01-01T00:00:00Z"}, headers=H(bdm)), 201).json()
    B["draft_mou"] = http.post(C("/placements/"), json=body, headers=H(hr1)).status_code
    B["bdm_activate"] = http.post(C(f"/agreements/{mou['id']}/status?status=active"), headers=H(bdm)).status_code
    expect(http.post(C(f"/agreements/{mou['id']}/status?status=active"), headers=H(o)), 200)
    pl = expect(http.post(C("/placements/"), json=body, headers=H(hr1)), 201).json()
    B["placement_fee_ignored_client_value"] = abs(pl["fee_amount"] - 150000) < 0.01
    B["recruiter_forced_to_self"] = pl["recruiter_id"] == S["ids"]["HR1"]
    B["bdm_change_active_terms"] = http.put(C(f"/agreements/{mou['id']}"), json={"fee_value": 25}, headers=H(bdm)).status_code
    expect(http.put(C(f"/agreements/{mou['id']}"), json={"fee_value": 20}, headers=H(o)), 200)
    B["fee_after_mou_edit"] = expect(http.get(C(f"/placements/{pl['id']}"), headers=H(o)), 200).json()["fee_amount"]
    B["invoice_before_join"] = http.post(C("/invoices/"), json={"placement_id": pl["id"]}, headers=H(bdm)).status_code
    expect(http.post(C(f"/placements/{pl['id']}/status"), json={"status": "joined"}, headers=H(hr1)), 200)
    issue = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=40)).isoformat()
    inv = expect(http.post(C("/invoices/"), json={"placement_id": pl["id"], "issue_date": issue}, headers=H(bdm)), 201).json()
    B["second_invoice"] = http.post(C("/invoices/"), json={"placement_id": pl["id"]}, headers=H(bdm)).status_code
    B.update(mou=mou, placement=pl, invoice=inv)
    # Cancel and re-raise with an owner override
    B["bdm_override_forbidden"] = False
    expect(http.post(C(f"/invoices/{inv['id']}/cancel"), json={"reason": "wrong client PO"}, headers=H(o)), 200)
    B["bdm_override_forbidden"] = http.post(C("/invoices/"), json={"placement_id": pl["id"], "amount_override": 1000,
                                                                  "override_reason": "x" * 5},
                                            headers=H(bdm)).status_code == 403
    B["override_needs_reason"] = http.post(C("/invoices/"), json={"placement_id": pl["id"], "amount_override": 140000},
                                           headers=H(o)).status_code == 422
    inv2 = expect(http.post(C("/invoices/"), json={"placement_id": pl["id"], "amount_override": 140000,
                                                  "override_reason": "Negotiated 140k with Acme", "issue_date": issue},
                            headers=H(o)), 201).json()
    expect(http.post(C(f"/invoices/{inv2['id']}/mark-paid"), headers=H(o)), 200)
    rate = [r for r in expect(http.get(C("/incentives/rules"), headers=H(hr1)), 200).json() if r["role"] == "hr"][0]["percentage"]
    incs = [i for i in expect(http.get(C("/incentives/"), headers=H(o)), 200).json()["data"] if i["invoice_id"] == inv2["id"]]
    hr_inc = [i for i in incs if i["user_id"] == S["ids"]["HR1"]]
    B.update(invoice2=inv2, incentive_ids=[i["id"] for i in incs], hr_rate=rate, invoice_amount=140000,
             expected_hr_incentive=round(140000 * rate / 100, 2),
             hr_incentive_amount=hr_inc[0]["amount"] if hr_inc else None,
             credited_people=sorted(i["user_id"] for i in incs))

    def void_count():
        return expect(http.get(C("/incentives/?status=void"), headers=H(o)), 200).json()["total"]

    # Scenario B: a paid invoice is cancelled (e.g. refund) -> its incentives are voided
    cand_b = expect(http.post(C("/candidates/"), json={"name": "Second Hire", "email": "second@qamail.in"}, headers=H(hr1)), 201).json()
    pl_b = expect(http.post(C("/placements/"), json={"candidate_id": cand_b["id"], "job_id": job["id"],
                                                     "offered_ctc": 800000, "bdm_id": S["ids"]["BDM"]},
                            headers=H(hr1)), 201).json()
    expect(http.post(C(f"/placements/{pl_b['id']}/status"), json={"status": "joined"}, headers=H(hr1)), 200)
    inv_b = expect(http.post(C("/invoices/"), json={"placement_id": pl_b["id"]}, headers=H(bdm)), 201).json()
    expect(http.post(C(f"/invoices/{inv_b['id']}/mark-paid"), headers=H(o)), 200)
    before = void_count()
    expect(http.post(C(f"/invoices/{inv_b['id']}/cancel"), json={"reason": "Client refund"}, headers=H(o)), 200)
    B["voided_on_cancel"] = void_count() - before

    # Scenario A continued: the candidate leaves within the guarantee period -> incentives clawed back
    before = void_count()
    expect(http.post(C(f"/placements/{pl['id']}/status"), json={"status": "left_in_guarantee"}, headers=H(hr1)), 200)
    B["voided_on_guarantee"] = void_count() - before

    # Scenario C: an unpaid invoice that is already past its due date -> overdue alert
    cand_c = expect(http.post(C("/candidates/"), json={"name": "Third Hire", "email": "third@qamail.in"}, headers=H(hr1)), 201).json()
    pl_c = expect(http.post(C("/placements/"), json={"candidate_id": cand_c["id"], "job_id": job["id"], "offered_ctc": 600000},
                            headers=H(hr1)), 201).json()
    expect(http.post(C(f"/placements/{pl_c['id']}/status"), json={"status": "joined"}, headers=H(hr1)), 200)
    B["inv_c"] = expect(http.post(C("/invoices/"), json={"placement_id": pl_c["id"], "issue_date": issue},
                                  headers=H(bdm)), 201).json()

    # Scenario D: an offer due to join within 24 h -> joining reminder (stays "offered")
    cand_d = expect(http.post(C("/candidates/"), json={"name": "Joining Soon", "email": "joining@qamail.in"}, headers=H(hr1)), 201).json()
    expect(http.post(C("/placements/"), json={
        "candidate_id": cand_d["id"], "job_id": job["id"], "offered_ctc": 900000,
        "expected_joining_date": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=20)).isoformat()},
        headers=H(hr1)), 201)


# ── P1 ────────────────────────────────────────────────────────────────────────

def p1_checks(S):
    sec = "P1"

    def duplicates():
        ev = []
        expect(http.post(C("/candidates/"), json={"name": "Dup Person", "email": "Dup.Person@QAMail.in",
                                                  "phone": "+91 98765-43210"}, headers=H(S["hr1"])), 201)
        r1 = http.post(C("/candidates/"), json={"name": "Dup 2", "email": "dup.person@qamail.in"}, headers=H(S["hr2"]))
        r2 = http.post(C("/candidates/"), json={"name": "Dup 3", "phone": "9876543210"}, headers=H(S["hr2"]))
        assert r1.status_code == 409 and r2.status_code == 409, (r1.status_code, r2.status_code)
        assert "Dup Person" in r1.json()["detail"], r1.text
        ev.append("same email (different case) and same phone (different format) -> 409 naming the existing record")
        chk = expect(http.get(C("/candidates/duplicates/check?phone=09876543210"), headers=H(S["hr1"])), 200).json()
        assert len(chk["duplicates"]) == 1, chk
        keep = expect(http.post(C("/candidates/"), json={"name": "Merge Keep", "email": "keep@qamail.in"}, headers=H(S["hr1"])), 201).json()
        dup = expect(http.post(C("/candidates/"), json={"name": "Merge Dup", "email": "dupe@qamail.in", "phone": "9000011111"},
                               headers=H(S["hr1"])), 201).json()
        job = S["billing"]["job"]
        expect(http.post(C(f"/jobs/{job['id']}/applications"), json={"candidate_id": dup["id"]}, headers=H(S["hr1"])), 201)
        expect(http.post(C(f"/candidates/{keep['id']}/merge/{dup['id']}"), headers=H(S["hr1"])), 403)
        merged = expect(http.post(C(f"/candidates/{keep['id']}/merge/{dup['id']}"), headers=H(S["owner"])), 200).json()
        expect(http.get(C(f"/candidates/{dup['id']}"), headers=H(S["owner"])), 404)
        job_apps = expect(http.get(C(f"/jobs/{job['id']}"), headers=H(S["owner"])), 200).json()["applications"]
        assert any(a["candidate_id"] == keep["id"] for a in job_apps) and merged["phone"] == "9000011111"
        ev.append("owner can merge duplicates: applications move over, missing fields filled, duplicate removed")
        # Portal: double-click apply -> one application only (unique index)
        job2 = post_live_job(S, S["recA"], {"title": "Race Job", "description": "Concurrency check role"})
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda _: http.post(P(f"/jobs/{job2['id']}/apply"), json={}, headers=H(S["cand2"])), range(8)))
        n = db_rows(PORTAL_DB, "SELECT COUNT(*) FROM applications WHERE job_id=?", (job2["id"],))[0][0]
        assert n == 1, f"{n} applications created"
        ev.append("portal: 8 simultaneous apply clicks -> exactly 1 application")
        return "; ".join(ev)
    run_check(sec, "P1-1", "Duplicate candidates", duplicates)

    def ats_workflow():
        ev = []
        app_id = S["appA"]
        ok = lambda st: http.patch(P(f"/jobs/applications/{app_id}"), json={"status": st}, headers=H(S["recA"]))  # noqa: E731
        expect(ok("interview"), 200)
        back = ok("applied")
        hired_early = ok("hired")
        assert back.status_code == 409 and hired_early.status_code == 409, (back.text, hired_early.text)
        expect(ok("offered"), 200)
        expect(ok("hired"), 200)
        final = ok("rejected")
        assert final.status_code == 409, final.text
        hist = expect(http.get(P(f"/jobs/applications/{app_id}/history"), headers=H(S["cand1"])), 200).json()
        assert [h["to_status"] for h in hist] == ["applied", "interview", "offered", "hired"], hist
        ev.append("portal: forward moves allowed; moving back, hiring without an offer and changing a hired "
                  "application are blocked (409); full history recorded")
        job3 = post_live_job(S, S["recA"], {"title": "Withdraw Job", "description": "Candidate withdraw path"})
        a3 = expect(http.post(P(f"/jobs/{job3['id']}/apply"), json={}, headers=H(S["cand2"])), 200).json()
        expect(http.patch(P(f"/jobs/applications/{a3['application_id']}"), json={"status": "withdrawn"},
                          headers=H(S["recA"])), 409)
        expect(http.post(P(f"/jobs/applications/{a3['application_id']}/withdraw"), headers=H(S["cand2"])), 200)
        ev.append("only the candidate can withdraw")
        b = S["billing"]
        cand = expect(http.post(C("/candidates/"), json={"name": "ATS Cand", "email": "ats@qamail.in"}, headers=H(S["hr1"])), 201).json()
        a = expect(http.post(C(f"/jobs/{b['job']['id']}/applications"), json={"candidate_id": cand["id"]}, headers=H(S["hr1"])), 201).json()
        dup = http.post(C(f"/jobs/{b['job']['id']}/applications"), json={"candidate_id": cand["id"]}, headers=H(S["hr1"]))
        st = lambda s: http.patch(C(f"/jobs/{b['job']['id']}/applications/{a['id']}/stage?stage={s}"), headers=H(S["hr1"]))  # noqa: E731
        assert dup.status_code == 409, dup.status_code
        assert st("bogus").status_code == 409 and st("hired").status_code == 409
        expect(st("interview"), 200)
        assert st("applied").status_code == 409
        expect(st("offer"), 200)
        status = expect(http.get(C(f"/candidates/{cand['id']}"), headers=H(S["hr1"])), 200).json()["status"]
        assert status == "offered", status
        ev.append("CRM: unknown stages, skipping to hired and moving back blocked; duplicate pipeline entry 409; "
                  "candidate status follows the stage")
        return "; ".join(ev)
    run_check(sec, "P1-2", "ATS workflow", ats_workflow)

    def mou_billing():
        B = S["billing"]
        assert B["no_mou"] == 409 and B["draft_mou"] == 409, (B["no_mou"], B["draft_mou"])
        assert B["bdm_activate"] == 403 and B["bdm_change_active_terms"] == 403
        assert abs(B["fee_after_mou_edit"] - 150000) < 0.01, B["fee_after_mou_edit"]
        assert B["invoice_before_join"] == 409 and B["second_invoice"] == 409
        inv = B["invoice"]
        assert abs(inv["amount"] - 150000) < 0.01 and abs(inv["gst_amount"] - 27000) < 0.01 \
            and abs(inv["total_amount"] - 177000) < 0.01, inv
        issue = dt.datetime.fromisoformat(inv["issue_date"].replace("Z", "+00:00"))
        due = dt.datetime.fromisoformat(inv["due_date"].replace("Z", "+00:00"))
        assert (due - issue).days == 30, (issue, due)
        return ("placement blocked with no MOU or a draft MOU; only the owner activates or changes active terms; "
                "fee = 12.5% x CTC 12,00,000 = 1,50,000 frozen at offer (unchanged after the MOU went to 20%); "
                "invoice only after joining, once per placement, 1,50,000 + 18% GST = 1,77,000, due in the "
                "MOU's 30 days")
    run_check(sec, "P1-3", "MOU / billing linkage", mou_billing)

    def audit_logs():
        o = S["owner"]
        inv_logs = expect(http.get(C("/audit-logs?entity_type=invoice"), headers=H(o)), 200).json()["data"]
        override = [l for l in inv_logs if l["changes"] and l["changes"].get("override_reason")]
        assert override and override[0]["changes"]["override_reason"] == "Negotiated 140k with Acme", inv_logs[:2]
        lead = expect(http.post(C("/leads/"), json={"company_name": "Audit Co", "contact_name": "Y"}, headers=H(S["bdm"])), 201).json()
        expect(http.put(C(f"/leads/{lead['id']}"), json={"budget": 500000, "temperature": "hot"}, headers=H(S["bdm"])), 200)
        lead_logs = expect(http.get(C(f"/audit-logs?entity_type=lead&entity_id={lead['id']}"), headers=H(o)), 200).json()["data"]
        upd = [l for l in lead_logs if l["action"] == "update"]
        assert upd and upd[0]["changes"]["temperature"] == {"from": "cold", "to": "hot"}, lead_logs
        sec_logs = expect(http.get(C("/audit-logs?action=security"), headers=H(o)), 200).json()["total"]
        p_logs = expect(http.get(P("/admin/audit-logs?action=auth.login_failed"), headers=H(S["admin"])), 200).json()
        locks = expect(http.get(P("/admin/audit-logs?action=auth.account_locked"), headers=H(S["admin"])), 200).json()
        st_logs = expect(http.get(P("/admin/audit-logs?action=application.status_changed"), headers=H(S["admin"])), 200).json()
        jobs_logs = expect(http.get(P("/admin/audit-logs?action=job."), headers=H(S["admin"])), 200).json()
        assert p_logs["total"] >= 1 and locks["total"] >= 1 and st_logs["total"] >= 1 and jobs_logs["total"] >= 1, \
            (p_logs["total"], locks["total"], st_logs["total"], jobs_logs["total"])
        assert sec_logs >= 1
        return (f"CRM records who changed what with before/after values (e.g. lead temperature cold->hot), the "
                f"invoice override reason, and {sec_logs} security events; portal admin log shows "
                f"{p_logs['total']} failed logins, {locks['total']} lockouts, {st_logs['total']} ATS status changes "
                f"and {jobs_logs['total']} job changes")
    run_check(sec, "P1-4", "Audit logs", audit_logs)


# ── Notifications ─────────────────────────────────────────────────────────────

def notification_checks(S):
    sec = "Notifications"
    o, bdm, hr1 = S["owner"], S["bdm"], S["hr1"]

    def candidate_updates():
        assert wait_for(lambda: [r for r in outbox(PORTAL_DB, "email_outbox", "application_status")
                                 if r[2] == "cand1@qamail.in"]), "portal status email missing"
        cand = expect(http.post(C("/candidates/"), json={"name": "Notify Cand", "email": "notify@qamail.in"}, headers=H(hr1)), 201).json()
        expect(http.put(C(f"/candidates/{cand['id']}"), json={"status": "shortlisted"}, headers=H(bdm)), 200)
        assert wait_for(lambda: [r for r in outbox(CRM_DB, "crm_email_outbox", "candidate_update") if r[2] == "notify@qamail.in"])
        n = expect(http.get(C("/notifications/"), headers=H(hr1)), 200).json()
        assert any("shortlisted" in x["title"] for x in n), n[:3]
        return "portal: candidate emailed on every status change; CRM: candidate emailed when shortlisted, " \
               "the recruiter who added them gets an in-app alert"
    run_check(sec, "N-1", "Candidate updates", candidate_updates)

    def interview_notifications():
        b = S["billing"]
        cand = expect(http.post(C("/candidates/"), json={"name": "Interview Cand", "email": "iv@qamail.in"}, headers=H(hr1)), 201).json()
        when = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3)).isoformat()
        iv = expect(http.post(C("/jobs/interviews"), json={"candidate_id": cand["id"], "job_id": b["job"]["id"],
                                                          "scheduled_at": when, "interviewer_ids": [S["ids"]["BDM"]]},
                              headers=H(hr1)), 201).json()
        assert wait_for(lambda: outbox(CRM_DB, "crm_email_outbox", "interview_scheduled"))
        assert any("Interview scheduled" in x["title"] for x in expect(http.get(C("/notifications/"), headers=H(bdm)), 200).json())
        new = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5)).isoformat()
        expect(http.patch(C(f"/jobs/interviews/{iv['id']}"), params={"scheduled_at": new}, headers=H(hr1)), 200)
        assert wait_for(lambda: outbox(CRM_DB, "crm_email_outbox", "interview_rescheduled"))
        past = http.post(C("/jobs/interviews"), json={"candidate_id": cand["id"], "job_id": b["job"]["id"],
                                                     "scheduled_at": "2020-01-01T10:00:00Z"}, headers=H(hr1))
        assert past.status_code == 422
        assert wait_for(lambda: [r for r in outbox(CRM_DB, "crm_email_outbox", "interview_reminder") if r[2] == "iv@qamail.in"],
                        timeout=20), "24h reminder not sent by the scheduler"
        return "scheduling emails the candidate and alerts interviewers in-app; rescheduling sends an update; " \
               "the scheduler sends a reminder inside 24 h; past times rejected"
    run_check(sec, "N-2", "Interview notifications", interview_notifications)

    def joining_notifications():
        assert outbox(CRM_DB, "crm_email_outbox", "joining"), "joining confirmation missing"
        assert wait_for(lambda: outbox(CRM_DB, "crm_email_outbox", "joining_reminder"), timeout=20), \
            "joining reminder (expected joining within 24 h) missing"
        notes = expect(http.get(C("/notifications/"), headers=H(o)), 200).json()
        assert any("joined" in x["title"] for x in notes), [x["title"] for x in notes[:5]]
        return "candidate gets a congratulations email on joining and a reminder the day before; owner/BDM/" \
               "recruiter get in-app joining alerts"
    run_check(sec, "N-3", "Joining notifications", joining_notifications)

    def client_notifications():
        joined = [r for r in outbox(CRM_DB, "crm_email_outbox", "client_joining") if r[2] == "asha@acme-corp.in"]
        invoiced = [r for r in outbox(CRM_DB, "crm_email_outbox", "client_invoice") if r[2] == "asha@acme-corp.in"]
        assert joined and invoiced, (joined, invoiced)
        return f"client's primary contact emailed on joining ({len(joined)}) and when invoices are raised ({len(invoiced)})"
    run_check(sec, "N-4", "Employer / client notifications", client_notifications)

    def hr_bdm_alerts():
        expect(http.post(C("/leads/"), json={"company_name": "Alert Lead", "contact_name": "Z",
                                             "assigned_to_id": S["ids"]["HR1"]}, headers=H(bdm)), 201)
        expect(http.post(C("/tasks/"), json={"title": "Call Acme", "assigned_to_id": S["ids"]["HR1"]}, headers=H(bdm)), 201)
        lead = expect(http.post(C("/leads/"), json={"company_name": "Followup Co", "contact_name": "F"}, headers=H(bdm)), 201).json()
        soon = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)).isoformat()
        expect(http.post(C(f"/leads/{lead['id']}/followups"), json={"scheduled_at": soon, "type": "call"}, headers=H(bdm)), 201)
        titles = [x["title"] for x in expect(http.get(C("/notifications/"), headers=H(hr1)), 200).json()]
        assert any("lead" in t.lower() for t in titles) and any("task" in t.lower() for t in titles), titles
        assert outbox(CRM_DB, "crm_email_outbox", "lead_assigned") and outbox(CRM_DB, "crm_email_outbox", "task_assigned")
        assert wait_for(lambda: outbox(CRM_DB, "crm_email_outbox", "followup_reminder"), timeout=20)
        bdm_titles = wait_for(lambda: [x["title"] for x in expect(http.get(C("/notifications/"), headers=H(bdm)), 200).json()
                                       if "overdue" in x["title"].lower()], timeout=20)
        assert bdm_titles, "overdue invoice alert missing"
        return "lead and task assignments alert the assignee (in-app + email); follow-ups remind 15 min ahead; " \
               "overdue invoices alert owners and BDMs"
    run_check(sec, "N-5", "HR / BDM alerts", hr_bdm_alerts)


# ── Database performance ──────────────────────────────────────────────────────

def seed_large_data(S):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    con = sqlite3.connect(PORTAL_DB)
    rec_id, comp_id = con.execute("SELECT r.id, r.company_id FROM recruiters r JOIN users u ON u.id=r.user_id "
                                  "WHERE u.email='reca@qamail.in'").fetchone()
    con.executemany("INSERT INTO jobs (company_id, recruiter_id, title, description, skills, location, "
                    "employment_type, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    [(comp_id, rec_id, f"Seed Job {i}", f"Seeded job {i} python react sql", '["python","sql"]',
                      ["Bangalore", "Pune", "Remote"][i % 3], "full_time", "published", now) for i in range(5000)])
    start_uid = con.execute("SELECT COALESCE(MAX(id),0) FROM users").fetchone()[0] + 1
    con.executemany("INSERT INTO users (id, name, email, password_hash, role, created_at, is_active, failed_login_count) "
                    "VALUES (?,?,?,?,?,?,1,0)",
                    [(start_uid + i, f"Seed Cand {i}", f"seed{i}@qamail.in", "x", "candidate", now) for i in range(10000)])
    con.executemany("INSERT INTO candidates (user_id, headline, skills, experience) VALUES (?,?,?,?)",
                    [(start_uid + i, "Engineer", '["python"]', "[]") for i in range(10000)])
    big_job = con.execute("INSERT INTO jobs (company_id, recruiter_id, title, description, status, created_at) "
                          "VALUES (?,?,?,?,?,?)", (comp_id, rec_id, "Big Job", "Many applicants here", "published", now)).lastrowid
    cand_ids = [r[0] for r in con.execute("SELECT id FROM candidates ORDER BY id DESC LIMIT 10000")]
    job_ids = [r[0] for r in con.execute("SELECT id FROM jobs WHERE title LIKE 'Seed Job %'")]
    rows = [(cid, big_job, "applied", now) for cid in cand_ids[:2000]]
    rows += [(cid, job_ids[i % len(job_ids)], "applied", now) for i, cid in enumerate(cand_ids[2000:])]
    con.executemany("INSERT INTO applications (candidate_id, job_id, status, applied_at) VALUES (?,?,?,?)", rows)
    con.commit()
    con.close()
    S["big_job"] = big_job

    con = sqlite3.connect(CRM_DB)
    con.executemany("INSERT INTO crm_candidates (name, email, phone, phone_normalized, skills, status, tags, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    [(f"Seed Person {i}", f"sp{i}@qamail.in", f"9{i:09d}", f"9{i:09d}", '["java"]', "new", "[]", now)
                     for i in range(10000)])
    con.executemany("INSERT INTO crm_leads (company_name, contact_name, status, temperature, tags, converted, "
                    "assigned_to_id, created_at) VALUES (?,?,?,?,?,0,?,?)",
                    [(f"Seed Lead {i}", "Seed", "new", "cold", "[]", S["ids"]["BDM"], now) for i in range(3000)])
    cbig = con.execute("INSERT INTO crm_jobs (title, positions, status, created_at) VALUES (?,1,'open',?)",
                       ("CRM Big Job", now)).lastrowid
    ccands = [r[0] for r in con.execute("SELECT id FROM crm_candidates WHERE name LIKE 'Seed Person %' LIMIT 2000")]
    con.executemany("INSERT INTO crm_applications (job_id, candidate_id, stage, applied_at, created_at) VALUES (?,?,?,?,?)",
                    [(cbig, c, "applied", now, now) for c in ccands])
    con.commit()
    con.close()
    S["crm_big_job"] = cbig


def timed(url, headers, n=15):
    times, codes = [], set()
    for _ in range(n):
        t0 = time.perf_counter()
        r = http.get(url, headers=headers)
        times.append((time.perf_counter() - t0) * 1000)
        codes.add(r.status_code)
    times.sort()
    return statistics.median(times), times[int(len(times) * 0.95) - 1], codes


def performance_checks(S):
    sec = "Database Performance"
    seed_large_data(S)
    ip = fresh_ip()
    endpoints = [
        ("portal GET /jobs (5,000+ jobs)", P("/jobs?limit=50"), H(ip=ip)),
        ("portal GET /jobs search", P("/jobs?q=python&location=Pune&limit=50"), H(ip=ip)),
        ("portal GET /jobs/{id}/applications (2,000 applicants)", P(f"/jobs/{S['big_job']}/applications?limit=200"), H(S["recA"], ip)),
        ("portal GET /admin/users", P("/admin/users?limit=50"), H(S["admin"], ip)),
        ("CRM GET /candidates (10,000+)", C("/candidates/?limit=50"), H(S["owner"], ip)),
        ("CRM GET /candidates search", C("/candidates/?search=Seed%20Person%2099&limit=50"), H(S["owner"], ip)),
        ("CRM GET /leads (3,000+)", C("/leads/?limit=50"), H(S["owner"], ip)),
        ("CRM GET /jobs/{id} (2,000 applicants)", C(f"/jobs/{S['crm_big_job']}"), H(S["owner"], ip)),
        ("CRM GET /analytics/overview", C("/analytics/overview"), H(S["owner"], ip)),
    ]
    timings = {}
    for name, url, hdr in endpoints:
        timings[name] = timed(url, hdr)

    def slow_queries():
        slow = {k: v for k, v in timings.items() if v[1] > 500 or v[2] != {200}}
        assert not slow, slow
        worst = max(timings.items(), key=lambda kv: kv[1][1])
        return "all key endpoints p95 < 500 ms on seeded data; slowest: " \
               f"{worst[0]} p95 {worst[1][1]:.0f} ms; requests over 1 s are logged as warnings"
    run_check(sec, "DB-1", "Slow queries", slow_queries)

    def indexes():
        portal_q = [
            ("applications by job", "SELECT * FROM applications WHERE job_id=1"),
            ("applications by candidate", "SELECT * FROM applications WHERE candidate_id=1"),
            ("published jobs", "SELECT * FROM jobs WHERE status='published'"),
            ("jobs by recruiter", "SELECT * FROM jobs WHERE recruiter_id=1"),
            ("user sessions", "SELECT * FROM user_sessions WHERE user_id=1"),
        ]
        crm_q = [
            ("applications by job", "SELECT * FROM crm_applications WHERE job_id=1"),
            ("candidate phone dedupe", "SELECT * FROM crm_candidates WHERE phone_normalized='9000000001'"),
            ("leads by assignee", "SELECT * FROM crm_leads WHERE assigned_to_id=1"),
            ("unread notifications", "SELECT * FROM crm_notifications WHERE user_id=1 AND read=0"),
            ("audit by record", "SELECT * FROM crm_activity_logs WHERE entity_type='lead' AND entity_id=1"),
            ("interviews by time", "SELECT * FROM crm_interviews WHERE scheduled_at > '2026-01-01'"),
        ]
        bad = []
        for db, qs in ((PORTAL_DB, portal_q), (CRM_DB, crm_q)):
            for label, sql in qs:
                plan = " ".join(str(r[-1]) for r in db_rows(db, "EXPLAIN QUERY PLAN " + sql))
                if "USING" not in plan or "INDEX" not in plan:
                    bad.append(f"{label}: {plan}")
        assert not bad, bad
        p_idx = db_rows(PORTAL_DB, "SELECT COUNT(*) FROM sqlite_master WHERE type='index'")[0][0]
        c_idx = db_rows(CRM_DB, "SELECT COUNT(*) FROM sqlite_master WHERE type='index'")[0][0]
        return f"{len(portal_q) + len(crm_q)} hot queries use indexes (SQLite EXPLAIN QUERY PLAN); " \
               f"{p_idx} indexes in the portal DB, {c_idx} in the CRM DB"
    run_check(sec, "DB-2", "Missing database indexes", indexes)

    def large_queries():
        jobs = expect(http.get(P("/jobs?limit=200"), headers=H(ip=ip)), 200).json()
        apps = expect(http.get(P(f"/jobs/{S['big_job']}/applications?limit=500"), headers=H(S["recA"], ip)), 200).json()
        cands = expect(http.get(C("/candidates/?limit=200"), headers=H(S["owner"], ip)), 200).json()
        cjob = expect(http.get(C(f"/jobs/{S['crm_big_job']}"), headers=H(S["owner"], ip)), 200).json()
        assert len(jobs) == 200 and len(apps) == 500 and len(cands["data"]) == 200 and cands["total"] >= 10000
        assert len(cjob["applications"]) == 2000 and cjob["applications"][0]["candidate_name"]
        return (f"5,000+ jobs, 10,000+ candidates, 2,000-applicant jobs: responses capped by page size, totals "
                f"correct ({cands['total']} CRM candidates), applicant lists load candidate names in one query "
                f"(p95 {timings['portal GET /jobs/{id}/applications (2,000 applicants)'][1]:.0f} ms / "
                f"{timings['CRM GET /jobs/{id} (2,000 applicants)'][1]:.0f} ms)")
    run_check(sec, "DB-3", "Large candidate / job queries", large_queries)

    def pagination():
        p1 = expect(http.get(C("/candidates/?page=1&limit=20"), headers=H(S["owner"], ip)), 200).json()
        p2 = expect(http.get(C("/candidates/?page=2&limit=20"), headers=H(S["owner"], ip)), 200).json()
        assert len(p1["data"]) == 20 and not {c["id"] for c in p1["data"]} & {c["id"] for c in p2["data"]}
        huge = [
            http.get(C("/candidates/?limit=100000"), headers=H(S["owner"], ip)).status_code,
            http.get(C("/leads/?limit=100000"), headers=H(S["owner"], ip)).status_code,
            http.get(C("/clients/?limit=100000"), headers=H(S["owner"], ip)).status_code,
            http.get(P("/jobs?limit=100000"), headers=H(ip=ip)).status_code,
            http.get(P("/admin/users?limit=100000"), headers=H(S["admin"], ip)).status_code,
        ]
        assert huge == [422] * 5, huge
        j1 = expect(http.get(P("/jobs?skip=0&limit=10"), headers=H(ip=ip)), 200).json()
        j2 = expect(http.get(P("/jobs?skip=10&limit=10"), headers=H(ip=ip)), 200).json()
        assert not {j["id"] for j in j1} & {j["id"] for j in j2}
        return "pages don't overlap; oversized page requests (limit=100000) rejected with 422 on 5 list endpoints"
    run_check(sec, "DB-4", "Pagination", pagination)

    def response_time():
        r = http.get(P("/jobs?limit=10"), headers=H(ip=ip))
        rc = http.get(C("/health"))
        assert "X-Response-Time" in r.headers and "X-Request-ID" in r.headers and "X-Response-Time" in rc.headers
        lines = [f"{k}: median {v[0]:.0f} ms / p95 {v[1]:.0f} ms" for k, v in timings.items()]
        return "every response carries X-Response-Time and X-Request-ID; " + "; ".join(lines)
    run_check(sec, "DB-5", "API response time", response_time)

    def pooling():
        def hit(i):
            if i % 2:
                return http.get(P("/jobs?limit=20"), headers=H(ip=fresh_ip())).status_code
            return http.get(C("/candidates/?limit=20"), headers=H(S["owner"], fresh_ip())).status_code
        with concurrent.futures.ThreadPoolExecutor(50) as ex:
            codes = list(ex.map(hit, range(200)))
        bad = [c for c in codes if c != 200]
        modes = (db_rows(PORTAL_DB, "PRAGMA journal_mode")[0][0], db_rows(CRM_DB, "PRAGMA journal_mode")[0][0])
        assert not bad and modes == ("wal", "wal"), (bad[:5], modes)
        return "200 concurrent requests (50 at a time) across both apps: all 200, no 'database is locked'; " \
               "SQLite in WAL mode with busy timeout; PostgreSQL deployments get a bounded pool (10 + 20 overflow, " \
               "pre-ping, recycle)"
    run_check(sec, "DB-6", "Connection pooling / concurrency", pooling)


# ── P2 ────────────────────────────────────────────────────────────────────────

def p2_checks(S):
    sec = "P2"

    def error_messages():
        r = http.post(P("/auth/register"), json={"name": "x", "email": "not-an-email", "password": "1"}, headers=H())
        rc = http.post(C("/candidates/"), json={"name": ""}, headers=H(S["hr1"]))
        assert r.status_code == 422 and isinstance(r.json()["detail"], str), r.text
        assert rc.status_code == 422 and isinstance(rc.json()["detail"], str), rc.text
        rule = http.post(P("/jobs"), json={"title": "Salary Check", "description": "Min above max salary",
                                           "salary_min": 50000, "salary_max": 1000}, headers=H(S["recA"]))
        assert rule.status_code == 422 and "greater than maximum" in rule.json()["detail"], rule.text
        nf = http.get(C("/candidates/999999"), headers=H(S["hr1"])).json()["detail"]
        return f"validation errors are readable sentences (e.g. \"{r.json()['detail'][:70]}\"); not-found: " \
               f"\"{nf}\"; unexpected errors return a generic message with a request id instead of a stack trace"
    run_check(sec, "P2-1", "Error messages", error_messages)

    def reports():
        csv_resp = expect(http.get(C("/reports/placements.csv"), headers=H(S["owner"])), 200)
        assert csv_resp.headers["content-type"].startswith("text/csv") and "candidate,job,client" in csv_resp.text
        expect(http.get(C("/reports/invoices.csv"), headers=H(S["hr1"])), 403)
        own = expect(http.get(C("/reports/incentives.csv"), headers=H(S["hr1"])), 200).text.strip().splitlines()
        rev = expect(http.get(C("/analytics/revenue"), headers=H(S["owner"])), 200).json()
        monthly = expect(http.get(C("/analytics/revenue/monthly"), headers=H(S["owner"])), 200).json()
        summary = expect(http.get(C("/analytics/placements/summary"), headers=H(S["hr1"])), 200).json()
        assert rev["collected"] > 0 and rev["invoiced"] >= rev["collected"] and monthly, rev
        return (f"CSV exports for leads/candidates/placements/invoices/incentives with role rules (HR: invoices 403, "
                f"own incentives only: {len(own) - 1} rows); revenue now from real invoices: invoiced "
                f"{rev['invoiced']:,.0f}, collected {rev['collected']:,.0f}, outstanding {rev['outstanding']:,.0f}, "
                f"overdue {rev['overdue']:,.0f}; monthly trend and placement funnel {summary}")
    run_check(sec, "P2-2", "Reports improvements", reports)

    def backup_recovery():
        sys.path.insert(0, os.path.join(ROOT, "deploy", "gcp"))
        import backup  # noqa: E402
        out = os.path.join(TMP, "crm-backup.db.gz")
        info = backup.backup_db(CRM_DB, out)
        assert backup.cmd_verify(out) == 0
        target = os.path.join(TMP, "restored.db")
        assert backup.cmd_restore(out, target, force=False) == 0
        a = db_rows(CRM_DB, "SELECT COUNT(*) FROM crm_candidates")[0][0]
        b = db_rows(target, "SELECT COUNT(*) FROM crm_candidates")[0][0]
        assert a == b and info["rows"] > 10000, (a, b, info)
        refused = backup.cmd_restore(out, target, force=False)
        assert refused == 1
        return (f"online backup of the live CRM DB while it was serving traffic ({info['tables']} tables, "
                f"{info['rows']:,} rows, {info['bytes']:,} bytes gz), integrity verified, restored copy has the "
                f"same {a:,} candidates; restore refuses to overwrite without --force and keeps the old DB; "
                "nightly cron + pre-deploy backup installed by update.sh")
    run_check(sec, "P2-3", "Backup / recovery", backup_recovery)

    def mobile_ux():
        import re
        issues, tables, forms = [], 0, 0
        for app_dir in (os.path.join(ROOT, "frontend", "app"), os.path.join(ROOT, "crm", "frontend", "app")):
            for dirpath, _, files in os.walk(app_dir):
                for name in files:
                    if not name.endswith(".tsx"):
                        continue
                    path = os.path.join(dirpath, name)
                    src = open(path, encoding="utf-8").read()
                    rel = os.path.relpath(path, ROOT)
                    n_tables = src.count("<table")
                    tables += n_tables
                    if n_tables and src.count("overflow-x-auto") < n_tables:
                        issues.append(f"{rel}: table without horizontal scroll")
                    for m in re.finditer(r'className="([^"]*)"', src):
                        cls = m.group(1).split()
                        if "grid-cols-2" in cls and not any(c.startswith(("sm:", "md:", "lg:")) and "grid-cols" in c for c in cls):
                            before = src[max(0, m.start() - 300):m.start()]
                            if "Quick Actions" not in before and "fine on phones" not in before:
                                issues.append(f"{rel}: 2-column grid never collapses on phones")
                        if "sm:grid-cols-2" in cls:
                            forms += 1
        layout = open(os.path.join(ROOT, "crm", "frontend", "app", "(crm)", "layout.tsx"), encoding="utf-8").read()
        if not ("setSidebarOpen" in layout and "lg:translate-x-0" in layout):
            issues.append("CRM sidebar has no mobile menu")
        hero = open(os.path.join(ROOT, "frontend", "components", "home", "hero-section.tsx"), encoding="utf-8").read()
        if "overflow-hidden" not in hero:
            issues.append("home hero can overflow on phones")
        assert not issues, issues
        return (f"static review of every page: all {tables} tables scroll horizontally on small screens, {forms} form "
                "grids collapse to one column below 640 px, CRM sidebar becomes a slide-out menu, wide decorative "
                "elements are clipped (no sideways scrolling); confirm visually on a phone after deploy")
    run_check(sec, "P2-4", "Mobile UX", mobile_ux)


# ── Beyond the checklist: website contact form and newsletter ────────────────

def extra_checks(S):
    import re
    sec = "Also fixed"

    def contact_form():
        ip = fresh_ip()
        body = {"name": "Priya Employer", "email": "Priya@Acme-Corp.in", "subject": "Hiring 5 Java developers",
                "message": "We need 5 Java developers in Pune." + chr(10) + "<script>alert(1)</script>"}
        r = expect(http.post(P("/contact"), json=body, headers=H(ip=ip)), 201).json()
        bad = http.post(P("/contact"), json={"name": "P", "email": "nope", "subject": "", "message": "hi"}, headers=H())
        assert bad.status_code == 422 and isinstance(bad.json()["detail"], str), bad.text
        for _ in range(4):
            expect(http.post(P("/contact"), json=body, headers=H(ip=ip)), 201)
        expect(http.post(P("/contact"), json=body, headers=H(ip=ip)), 429)
        rows = wait_for(lambda: [x for x in db_rows(PORTAL_DB, "SELECT to_email, status, html FROM email_outbox "
                                                              "WHERE category='contact_enquiry'") if x[1] == "sent"])
        assert rows and rows[0][0] == "bdm@jobsnexgen.com", rows[:1]
        assert "&lt;script&gt;" in rows[0][2] and "<script>" not in rows[0][2], "message not escaped in the email"
        expect(http.get(P("/admin/enquiries"), headers=H(S["cand1"])), 403)
        listing = expect(http.get(P("/admin/enquiries?status=new"), headers=H(S["admin"])), 200).json()
        mine = [e for e in listing["data"] if e["id"] == r["id"]]
        assert mine and mine[0]["email"] == "priya@acme-corp.in", listing
        expect(http.post(P(f"/admin/enquiries/{r['id']}/handled"), headers=H(S["admin"])), 200)
        after = expect(http.get(P("/admin/enquiries?status=new"), headers=H(S["admin"])), 200).json()
        stats = expect(http.get(P("/admin/stats"), headers=H(S["admin"])), 200).json()
        assert after["new"] == listing["new"] - 1 and stats["new_enquiries"] == after["new"], (after, stats)
        return (f"message saved (#{r['id']}) and emailed to bdm@jobsnexgen.com (delivered); HTML in the message is "
                f"escaped; bad input -> readable 422; 6th message from one IP in an hour -> 429; admin sees it under "
                f"Enquiries ({listing['new']} new) and can mark it handled; candidates can't see enquiries (403)")
    run_check(sec, "X-1", "Website contact form actually delivers enquiries (was a fake 'sent')", contact_form)

    def newsletter():
        email = "alerts.reader@qamail.in"
        r = expect(http.post(P("/newsletter/subscribe"), json={"email": email.upper()}, headers=H()), 200).json()
        assert r["status"] == "pending", r
        html = wait_for(lambda: db_rows(PORTAL_DB, "SELECT html FROM email_outbox WHERE category='newsletter_confirm' "
                                                   "AND to_email=?", (email,)))
        m = re.search(r"action=confirm&(?:amp;)?email=([^&\"]+)&(?:amp;)?sig=([0-9a-f]+)", html[0][0])
        assert m, "no confirmation link in the email"
        expect(http.post(P("/newsletter/confirm"), json={"email": email, "sig": "0" * 64}, headers=H()), 400)
        expect(http.post(P("/newsletter/confirm"), json={"email": email, "sig": m.group(2)}, headers=H()), 200)
        again = expect(http.post(P("/newsletter/subscribe"), json={"email": email}, headers=H()), 200).json()
        assert again["status"] == "subscribed", again
        post_live_job(S, S["recA"], {"title": "Weekly Alert Test Role", "description": "Posted for the job-alert check",
                                     "status": "published", "location": "Pune"})
        expect(http.post(P("/admin/newsletter/send-digest"), headers=H(S["recA"])), 403)
        sent = expect(http.post(P("/admin/newsletter/send-digest"), headers=H(S["admin"])), 200).json()
        assert sent["queued"] == 1, sent
        digest = wait_for(lambda: [x for x in db_rows(PORTAL_DB, "SELECT status, html, subject FROM email_outbox "
                                                                 "WHERE category='newsletter_digest' AND to_email=?",
                                                      (email,)) if x[0] == "sent"])
        assert digest and "Weekly Alert Test Role" in digest[0][1] and "action=unsubscribe" in digest[0][1], digest[:1]
        twice = expect(http.post(P("/admin/newsletter/send-digest"), headers=H(S["admin"])), 200).json()
        assert twice["queued"] == 0, twice
        u = re.search(r"action=unsubscribe&(?:amp;)?email=([^&\"]+)&(?:amp;)?sig=([0-9a-f]+)", digest[0][1])
        expect(http.post(P("/newsletter/unsubscribe"), json={"email": email, "sig": u.group(2)}, headers=H()), 200)
        subs = expect(http.get(P("/admin/newsletter?status=unsubscribed"), headers=H(S["admin"])), 200).json()
        assert any(x["email"] == email for x in subs["data"]), subs
        return (f"sign-up saved and a confirmation email sent (double opt-in); forged link -> 400, real link confirms; "
                f"weekly new-jobs email ('{digest[0][2]}') delivered with job links and an unsubscribe link; pressing "
                f"'send now' twice doesn't double-send; unsubscribe works and shows in the admin list")
    run_check(sec, "X-2", "Newsletter sign-up, weekly job alerts and unsubscribe (was a dead form)", newsletter)


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE C: job approval, job details and the automatic portal -> CRM sync
#  (meeting feedback: portal jobs never reached the CRM; missing job fields)
# ══════════════════════════════════════════════════════════════════════════════

def phase_c():
    print("\n== Phase C: job approval, job fields and portal -> CRM sync (fresh databases) ==")
    portal_sync_srv.start(EMAIL_BACKEND="console")
    crm_sync_srv.start(EMAIL_BACKEND="console")
    sec = "Meeting feedback"
    T = {}
    seed_portal_admin("admin2@qamail.in", "AdminQa123!", portal_sync_srv)
    T["admin"] = expect(p_login("admin2@qamail.in", "AdminQa123!"), 200).json()["access_token"]
    T["free"] = p_register("Free Lancer", "freelancer@qamail.in", "recruiter", "Swiggy Partner Agency")["access_token"]
    T["cand"] = p_register("Ravi Kumar", "ravi@qamail.in")["access_token"]
    T["owner"] = expect(http.post(C("/auth/register"), json={"name": "Sync Owner", "email": "syncowner@qamail.in",
                                                            "password": "CrmTest123!"}, headers=H()), 201).json()["access_token"]
    expect(http.post(C("/users/"), json={"name": "Tejaswini HR", "email": "tejaswini@qamail.in", "password": "CrmTest123!",
                                        "role": "hr"}, headers=H(T["owner"])), 201)
    T["hr"] = c_token("tejaswini@qamail.in")

    def outbox_to(category, email):
        return wait_for(lambda: db_rows(SYNC_PORTAL_DB, "SELECT id FROM email_outbox WHERE category=? AND to_email=?",
                                        (category, email)))

    def approval():
        body = {"title": "Swiggy Delivery Executives", "description": "Deliver food orders on a two-wheeler",
                "location": "Bengaluru", "locality": "JP Nagar", "education": "10th", "salary_min": 18000,
                "salary_max": 25000, "salary_period": "month", "employment_type": "full_time"}
        job = expect(http.post(P("/jobs"), json=body, headers=H(T["free"])), 201).json()
        assert job["status"] == "pending", job
        jid = T["job"] = job["id"]
        expect(http.get(P(f"/jobs/{jid}"), headers=H()), 404)
        assert all(j["id"] != jid for j in expect(http.get(P("/jobs"), headers=H()), 200).json())
        assert outbox_to("job_pending", "admin2@qamail.in"), "admin not emailed about the pending job"
        again = expect(http.patch(P(f"/jobs/{jid}"), json={"status": "published"}, headers=H(T["free"])), 200).json()
        assert again["status"] == "pending", again
        expect(http.patch(P(f"/jobs/{jid}"), json={"status": "rejected"}, headers=H(T["free"])), 422)
        expect(http.post(P(f"/admin/jobs/{jid}/approve"), headers=H(T["free"])), 403)
        rej = expect(http.post(P(f"/admin/jobs/{jid}/reject"), json={"reason": "Please add the shift timings"},
                               headers=H(T["admin"])), 200).json()
        assert rej["status"] == "rejected", rej
        assert outbox_to("job_review", "freelancer@qamail.in"), "poster not told about the rejection"
        mine = expect(http.get(P("/jobs/recruiter/my"), headers=H(T["free"])), 200).json()
        assert mine[0]["review_note"] == "Please add the shift timings", mine[0]
        edited = expect(http.patch(P(f"/jobs/{jid}"), json={"description": "Deliver food orders on a two-wheeler. "
                                                            "Shifts 7am-3pm or 3pm-11pm."}, headers=H(T["free"])), 200).json()
        assert edited["status"] == "pending", edited
        queue = expect(http.get(P("/admin/jobs?status=pending"), headers=H(T["admin"])), 200).json()
        assert any(q["id"] == jid and q["posted_by_email"] == "freelancer@qamail.in" for q in queue), queue
        expect(http.post(P(f"/admin/jobs/{jid}/approve"), headers=H(T["admin"])), 200)
        expect(http.get(P(f"/jobs/{jid}"), headers=H()), 200)
        closed = expect(http.patch(P(f"/jobs/{jid}"), json={"status": "closed"}, headers=H(T["free"])), 200).json()
        reopened = expect(http.patch(P(f"/jobs/{jid}"), json={"status": "published"}, headers=H(T["free"])), 200).json()
        assert closed["status"] == "closed" and reopened["status"] == "published", (closed, reopened)
        aj = expect(http.post(P("/jobs"), json={"title": "Fat Cutting Helper", "description": "Meat processing unit helper",
                                                 "location": "Bengaluru", "locality": "Peenya", "education": "any",
                                                 "salary_min": 15000, "salary_max": 18000, "salary_period": "month"},
                                headers=H(T["admin"])), 201).json()
        assert aj["status"] == "published" and aj["company"]["name"] == "JobsNexGen", aj
        T["admin_job"] = aj["id"]
        stats = expect(http.get(P("/admin/stats"), headers=H(T["admin"])), 200).json()
        return ("a freelancer's job starts 'awaiting approval' and is hidden from candidates; admins are emailed; "
                "the poster can't approve it (403); a rejection reason reaches the poster by email and on their "
                "dashboard; editing sends it back for review; after approval it is live and can be closed and "
                f"reopened without another review; an admin's own job goes live at once (pending now: {stats['pending_jobs']})")
    run_check(sec, "X-3", "Freelancer job posts need admin approval", approval)

    def job_fields():
        expect(http.post(P("/jobs"), json={"title": "Bad Edu", "description": "Invalid education value",
                                           "education": "phd"}, headers=H(T["admin"])), 422)
        expect(http.post(P("/jobs"), json={"title": "Bad Period", "description": "Invalid salary period",
                                           "salary_min": 1, "salary_period": "week"}, headers=H(T["admin"])), 422)
        yearly = expect(http.post(P("/jobs"), json={"title": "Store Manager", "description": "Run a retail store team",
                                                     "location": "Mysuru", "education": "graduate", "salary_min": 600000,
                                                     "salary_max": 720000, "salary_period": "year"},
                                  headers=H(T["admin"])), 201).json()["id"]

        def ids(**params):
            return {j["id"] for j in expect(http.get(P("/jobs"), params=params, headers=H()), 200).json()}
        jid = T["job"]
        assert jid in ids(education="12th") and yearly not in ids(education="12th") and yearly in ids(education="postgraduate")
        assert jid in ids(location="JP Nagar") and jid in ids(locality="jp nagar") and yearly not in ids(location="JP Nagar")
        assert jid in ids(min_monthly_salary=20000) and jid not in ids(min_monthly_salary=30000)
        assert yearly in ids(min_monthly_salary=55000) and yearly not in ids(min_monthly_salary=65000)
        d = expect(http.get(P(f"/jobs/{jid}"), headers=H()), 200).json()
        assert (d["education"], d["locality"], d["salary_period"]) == ("10th", "JP Nagar", "month"), d
        up = expect(http.post(P("/upload/resume"), files={"file": ("cv.pdf", PDF, "application/pdf")},
                              headers=H(T["cand"])), 200).json()
        expect(http.post(P(f"/jobs/{jid}/apply"), json={"education": "masters"}, headers=H(T["cand"])), 422)
        expect(http.post(P(f"/jobs/{jid}/apply"), json={
            "full_name": "Ravi Kumar", "phone": "+91 98450 12345", "years_experience": 2, "education": "12th",
            "expected_salary": 22000, "current_location": "Jayanagar, Bengaluru", "resume_url": up["url"]},
            headers=H(T["cand"])), 200)
        apps = expect(http.get(P(f"/jobs/{jid}/applications"), headers=H(T["free"])), 200).json()
        a = apps[0]
        assert (a["education"], a["expected_salary"], a["current_location"]) == ("12th", 22000, "Jayanagar, Bengaluru"), a
        T["app"] = a["id"]
        return ("jobs store minimum education, city + locality and salary per month or per year (bad values -> 422); "
                "public search filters by qualification (12th-pass sees 10th jobs, not graduate jobs), by area "
                "('JP Nagar'), and by monthly pay, comparing yearly salaries fairly (7.2L/year = 60k/month); "
                "applicants give education, expected salary and current location, and the recruiter sees them")
    run_check(sec, "X-4", "Job form: education, salary per month/year, city and locality; better filters", job_fields)

    def crm_job(portal_id):
        rows = expect(http.get(C("/jobs/"), params={"limit": 100}, headers=H(T["owner"])), 200).json()["data"]
        return next((j for j in rows if j.get("portal_job_id") == portal_id), None)

    def crm_sync():
        st = expect(http.get(C("/portal/status"), headers=H(T["hr"])), 200).json()
        assert st["configured"], st
        # The scheduler syncs on its own every few seconds here (every 2 minutes in production)
        j = wait_for(lambda: (lambda x: x if x and x["status"] == "open" else None)(crm_job(T["job"])), timeout=40)
        assert j, f"portal job never reached the CRM: {expect(http.get(C('/portal/status'), headers=H(T['owner'])), 200).json()}"
        assert (j["education"], j["locality"], j["salary_period"], j["source"]) == ("10th", "JP Nagar", "month", "portal"), j
        assert "freelancer@qamail.in" in (j.get("posted_by") or ""), j
        overview = expect(http.get(C("/analytics/overview"), headers=H(T["owner"])), 200).json()
        assert overview["jobs"]["open"] >= 2, overview["jobs"]
        detail = wait_for(lambda: (lambda d: d if d["applications"] else None)(
            expect(http.get(C(f"/jobs/{j['id']}"), headers=H(T["owner"])), 200).json()), timeout=20)
        app = detail["applications"][0]
        assert app["candidate_name"] == "Ravi Kumar" and app["candidate_education"] == "12th", app
        assert app["candidate_expected_salary"] == "₹22,000/month" and app["candidate_location"] == "Jayanagar, Bengaluru", app
        cand = expect(http.get(C(f"/candidates/{app['candidate_id']}"), headers=H(T["owner"])), 200).json()
        assert cand["resume_url"] and cand["source"] == "portal", cand
        # The pipeline follows the portal
        expect(http.patch(P(f"/jobs/applications/{T['app']}"), json={"status": "screening"}, headers=H(T["free"])), 200)
        expect(http.post(C("/portal/sync"), headers=H(T["hr"])), 403)
        res = expect(http.post(C("/portal/sync"), headers=H(T["owner"])), 200).json()
        stage = expect(http.get(C(f"/jobs/{j['id']}"), headers=H(T["owner"])), 200).json()["applications"][0]["stage"]
        assert stage == "screening", (stage, res)
        # A job waiting for approval is "on hold" in the CRM; deleting it on the portal closes it
        pend = expect(http.post(P("/jobs"), json={"title": "Warehouse Packer", "description": "Pack and label parcels",
                                                   "location": "Bengaluru", "education": "10th"}, headers=H(T["free"])), 201).json()
        expect(http.post(C("/portal/sync"), headers=H(T["owner"])), 200)
        pj = crm_job(pend["id"])
        assert pj and pj["status"] == "on_hold" and pj["portal_status"] == "pending", pj
        # A CRM user's own status choice survives later syncs
        expect(http.put(C(f"/jobs/{j['id']}"), json={"status": "filled"}, headers=H(T["owner"])), 200)
        expect(http.delete(P(f"/jobs/{pend['id']}"), headers=H(T["free"])), 204)
        expect(http.post(C("/portal/sync"), headers=H(T["owner"])), 200)
        assert crm_job(pend["id"])["status"] == "closed" and crm_job(T["job"])["status"] == "filled"
        st = expect(http.get(C("/portal/status"), headers=H(T["owner"])), 200).json()
        assert st["last_success_at"] and not st["last_error"], st
        return (f"the approved portal job appeared in the CRM by itself as an open job with education, locality, monthly "
                f"pay and who posted it; the dashboard's Open Jobs count is {overview['jobs']['open']}; the applicant "
                "became a CRM candidate with education, expected salary, location and their resume; moving the "
                "application on the portal moved it in the CRM; a job awaiting approval shows 'on hold' and a deleted "
                "one is closed; a CRM user's own status is kept; HR can see the sync status but only owner/BDM can "
                "press Sync now")
    run_check(sec, "X-5", "Portal jobs and applicants reach the CRM automatically (Open Jobs no longer 0)", crm_sync)

    def link_security():
        base = f"http://127.0.0.1:{PORTAL_PORT}/api/v1/integrations/crm/jobs"
        no_key = httpx.get(base).status_code
        wrong = httpx.get(base, headers={"X-Integration-Key": "wrong-key"}).status_code
        via_site = httpx.get(base, headers={"X-Integration-Key": QA_INTEGRATION_KEY, "X-Forwarded-For": "203.0.113.9"}).status_code
        ok = httpx.get(base, headers={"X-Integration-Key": QA_INTEGRATION_KEY}).status_code
        assert (no_key, wrong, via_site, ok) == (403, 403, 404, 200), (no_key, wrong, via_site, ok)
        return ("the portal's CRM feed refuses requests without the key (403) or with a wrong key (403), and refuses "
                "anything arriving through the public website even with the right key (404); only the CRM on the same "
                "server can read it")
    run_check(sec, "X-6", "The portal-CRM link is private", link_security)

    portal_sync_srv.stop()
    crm_sync_srv.stop()


# ══════════════════════════════════════════════════════════════════════════════

def write_reports():
    with open(os.path.join(ROOT, "qa", "results.json"), "w", encoding="utf-8") as f:
        json.dump({"run_at": dt.datetime.now().isoformat(timespec="seconds"), "results": RESULTS}, f, indent=2)
    lines = ["# JobsNexGen checklist results", "",
             f"Run at {dt.datetime.now():%Y-%m-%d %H:%M}. {sum(r['status'] == 'PASS' for r in RESULTS)} PASS, "
             f"{sum(r['status'] == 'FAIL' for r in RESULTS)} FAIL.", "",
             "| Section | Item | Check | Result | Evidence |", "|---|---|---|---|---|"]
    for r in RESULTS:
        lines.append(f"| {r['section']} | {r['item']} | {r['title']} | {r['status']} | "
                     f"{r['evidence'].replace('|', '/')} |")
    with open(os.path.join(ROOT, "qa", "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    print(f"temp dir: {TMP}")
    try:
        phase_a()
        phase_b()
        phase_c()
    finally:
        portal.stop()
        crm.stop()
        portal_sync_srv.stop()
        crm_sync_srv.stop()
        write_reports()
    passed = sum(r["status"] == "PASS" for r in RESULTS)
    print(f"\n{passed}/{len(RESULTS)} PASS  ->  qa/results.md")
    if os.environ.get("QA_KEEP") != "1":
        shutil.rmtree(TMP, ignore_errors=True)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
