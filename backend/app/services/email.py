"""
Email service using Python's built-in smtplib (no external API keys needed).
SMTP: mail.jobsnexgen.com  port 465 SSL
From: bdm@jobsnexgen.com
"""
import html as _html
import logging
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── SMTP config ───────────────────────────────────────────────────────────────
SMTP_HOST     = "smtp.hostinger.com"
SMTP_PORT     = 465
SMTP_USER     = "bdm@jobsnexgen.com"
SMTP_PASSWORD = "Jobsnexgen@2026"
FROM_NAME     = "JobsNexGen"
FROM_ADDR     = "bdm@jobsnexgen.com"

# ── Brand colours ─────────────────────────────────────────────────────────────
_BLUE   = "#3B82F6"
_PURPLE = "#8B5CF6"
_DARK   = "#0F172A"
_CARD   = "#1E293B"
_MUTED  = "#94A3B8"
_WHITE  = "#F8FAFC"


# ── Low-level sender ──────────────────────────────────────────────────────────
def send_raw(to_email: str, to_name: str, subject: str, html: str) -> tuple[bool, str | None]:
    """One delivery attempt. Returns (ok, error). Used by the outbox, which retries."""
    if settings.EMAIL_BACKEND == "console":
        logger.info(f"[EMAIL:console] '{subject}' → {to_email}")
        return True, None
    if settings.EMAIL_BACKEND == "fail":  # used by the QA suite to exercise retries
        return False, "simulated delivery failure (EMAIL_BACKEND=fail)"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{FROM_ADDR}>"
    msg["To"]      = f"{_e(to_name)} <{to_email}>" if to_name else to_email
    msg["Reply-To"] = FROM_ADDR
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_ADDR, [to_email], msg.as_string())
        logger.info(f"[EMAIL] Sent '{subject}' → {to_email}")
        return True, None
    except Exception as exc:
        logger.error(f"[EMAIL] Failed to send '{subject}' → {to_email}: {exc}")
        return False, f"{type(exc).__name__}: {exc}"


def _send_async(to_email: str, to_name: str, subject: str, html: str, category: str = "general") -> None:
    """Queue the email in the outbox; it is sent in the background and retried on failure."""
    from app.services.outbox import enqueue_email
    try:
        enqueue_email(category, to_email, to_name, subject, html)
    except Exception:
        logger.exception(f"[EMAIL] could not queue '{subject}' → {to_email}")


def _e(value) -> str:
    """HTML-escape user-supplied text before it goes into an email body."""
    return _html.escape(str(value if value is not None else ""))


def _wrap(body_html: str, cta_url: str = "", cta_label: str = "", footer_note: str = "") -> str:
    cta_block = ""
    if cta_url and cta_label:
        cta_block = f"""
        <a href="{cta_url}"
           style="display:inline-block;margin-top:20px;padding:13px 28px;
                  background:linear-gradient(135deg,{_BLUE},{_PURPLE});
                  color:#fff;text-decoration:none;border-radius:8px;
                  font-weight:700;font-size:14px;letter-spacing:.3px">
          {cta_label}
        </a>"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#060f1e;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#060f1e;padding:32px 16px">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:{_DARK};border-radius:16px;overflow:hidden;
                    border:1px solid rgba(255,255,255,.08);max-width:600px;width:100%">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,{_BLUE}22,{_PURPLE}22);
                     padding:28px 36px;border-bottom:1px solid rgba(255,255,255,.08)">
            <span style="font-size:22px;font-weight:800;letter-spacing:-.5px">
              <span style="color:#1B75BB">Jobs</span><span style="color:#F7941D">Nex</span><span style="color:#39B54A">Gen</span>
            </span>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px 36px;color:{_WHITE}">
            {body_html}
            {cta_block}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 36px;border-top:1px solid rgba(255,255,255,.06)">
            <p style="margin:0;color:#475569;font-size:12px">
              © 2025 JobsNexGen · Bengaluru, Karnataka 560045
              · <a href="https://jobsnexgen.com" style="color:{_BLUE};text-decoration:none">jobsnexgen.com</a>
              · <a href="mailto:support@jobsnexgen.in" style="color:{_BLUE};text-decoration:none">support@jobsnexgen.in</a>
            </p>
            <p style="margin:6px 0 0;color:#334155;font-size:11px">
              {footer_note or "You are receiving this email because an action was taken on your JobsNexGen account."}
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body></html>"""


def _stat_box(label: str, value: str, color: str) -> str:
    value = _e(value)
    return f"""
    <td style="text-align:center;padding:12px 16px;
               background:{_CARD};border-radius:8px;
               border:1px solid rgba(255,255,255,.06)">
      <div style="font-size:20px;font-weight:800;color:{color}">{value}</div>
      <div style="font-size:11px;color:{_MUTED};margin-top:2px">{label}</div>
    </td>"""


# ── Public API ────────────────────────────────────────────────────────────────

def send_welcome_email(to_email: str, name: str) -> None:
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">Welcome to JobsNexGen! 🎉</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Hi <strong style="color:{_WHITE}">{_e(name)}</strong>,</p>
    <p style="margin:0 0 16px;color:{_MUTED}">
      Your account is ready. Here's what you can do right now:
    </p>
    <ul style="color:{_MUTED};padding-left:20px;line-height:1.9">
      <li>Browse thousands of jobs with AI-powered recommendations</li>
      <li>Build your professional resume with our Resume Builder</li>
      <li>Track all your applications in the ATS Pipeline</li>
      <li>Get career advice from our AI assistant</li>
    </ul>"""
    html = _wrap(body, f"{settings.FRONTEND_URL}/jobs", "Browse Jobs →")
    _send_async(to_email, name, "Welcome to JobsNexGen! 🎉", html, category="welcome")


def send_application_received_email(
    to_email: str, name: str, job_title: str, company: str
) -> None:
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">Application Received ✅</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Hi <strong style="color:{_WHITE}">{_e(name)}</strong>,</p>
    <p style="margin:0 0 20px;color:{_MUTED}">
      Great news — your application has been successfully submitted.
      The recruiter will review it shortly.
    </p>
    <table cellpadding="0" cellspacing="12" style="width:100%;border-collapse:separate">
      <tr>
        {_stat_box("Position", job_title, _BLUE)}
        {_stat_box("Company", company, _PURPLE)}
        {_stat_box("Status", "Applied", "#10B981")}
      </tr>
    </table>
    <p style="margin:20px 0 0;color:{_MUTED};font-size:13px">
      Track your application status in real-time on your dashboard.
    </p>"""
    html = _wrap(body, f"{settings.FRONTEND_URL}/ats", "Track Application →")
    _send_async(to_email, name, f"Application received – {job_title}", html, category="application_received")


def send_recruiter_new_application_email(
    to_email: str,
    recruiter_name: str,
    candidate_name: str,
    job_title: str,
    candidate_email: str,
    years_exp: int | None,
) -> None:
    exp_str = f"{years_exp} yr{'s' if (years_exp or 0) != 1 else ''}" if years_exp else "Not specified"
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">New Application Received 📬</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Hi <strong style="color:{_WHITE}">{_e(recruiter_name)}</strong>,</p>
    <p style="margin:0 0 20px;color:{_MUTED}">
      A new candidate has applied for your job posting.
    </p>
    <table cellpadding="0" cellspacing="12" style="width:100%;border-collapse:separate">
      <tr>
        {_stat_box("Job", job_title, _BLUE)}
        {_stat_box("Candidate", candidate_name, _PURPLE)}
        {_stat_box("Experience", exp_str, "#F59E0B")}
      </tr>
    </table>
    <div style="margin-top:20px;background:{_CARD};border-radius:8px;padding:14px 16px;
                border:1px solid rgba(255,255,255,.06)">
      <p style="margin:0;color:{_MUTED};font-size:13px">
        Candidate email: <a href="mailto:{_e(candidate_email)}"
          style="color:{_BLUE};text-decoration:none">{_e(candidate_email)}</a>
      </p>
    </div>
    <p style="margin:16px 0 0;color:{_MUTED};font-size:13px">
      Review their profile, ATS score, and resume on your dashboard.
    </p>"""
    html = _wrap(body, f"{settings.FRONTEND_URL}/dashboard/recruiter", "View Application →")
    _send_async(to_email, recruiter_name, f"New applicant for '{job_title}' – {candidate_name}", html, category="recruiter_new_application")


def send_status_update_email(
    to_email: str, name: str, job_title: str, new_status: str, company: str = ""
) -> None:
    status_map = {
        "screening": ("Moved to Screening 🔍",  "#F59E0B", "Your profile is being reviewed by the hiring team."),
        "interview": ("Interview Invitation 🎯", _PURPLE,   "Congratulations! You have been shortlisted for an interview. Check your messages for details."),
        "offered":   ("Job Offer Received 🎉",  "#10B981",  "Congratulations! You have received a job offer. Please log in to review and respond."),
        "hired":     ("You're Hired! 🎉",       "#10B981",  "Congratulations! The employer has confirmed your hiring. They will contact you with joining details."),
        "withdrawn": ("Application Withdrawn",   "#64748B",  "Your application has been withdrawn."),
        "rejected":  ("Application Update",      "#EF4444",  "Thank you for applying. After careful consideration, the team has decided to move forward with other candidates. We encourage you to keep exploring opportunities on JobsNexGen."),
    }
    label, color, message = status_map.get(
        new_status,
        (f"Status Updated to {new_status.title()}", _BLUE, "Your application status has been updated.")
    )
    company_line = f" at <strong style='color:{_WHITE}'>{_e(company)}</strong>" if company else ""
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">{label}</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Hi <strong style="color:{_WHITE}">{_e(name)}</strong>,</p>
    <div style="background:{_CARD};border-left:4px solid {color};border-radius:0 8px 8px 0;
                padding:14px 18px;margin-bottom:20px">
      <p style="margin:0;color:{_MUTED};font-size:13px">
        Your application for <strong style="color:{_WHITE}">{_e(job_title)}</strong>{company_line}
        has been updated.
      </p>
      <p style="margin:8px 0 0;color:{color};font-weight:700;font-size:15px">
        Status: {new_status.replace('_', ' ').title()}
      </p>
    </div>
    <p style="margin:0;color:{_MUTED};font-size:13px">{message}</p>"""
    html = _wrap(body, f"{settings.FRONTEND_URL}/ats", "View Application →")
    _send_async(to_email, name, f"{label} – {job_title}", html, category="application_status")


def send_message_notification_email(
    to_email: str,
    to_name: str,
    sender_name: str,
    job_title: str,
    message_type: str,
    content: str,
) -> None:
    type_labels = {
        "message":          ("New Message 💬",           _BLUE),
        "approval":         ("You've Been Shortlisted ✅", "#10B981"),
        "interview_invite": ("Interview Invitation 🎯",   _PURPLE),
        "offer":            ("Job Offer Received 🎉",     "#10B981"),
        "rejection":        ("Application Update",         "#EF4444"),
    }
    label, color = type_labels.get(message_type, ("New Message 💬", _BLUE))
    preview = content[:300] + ("…" if len(content) > 300 else "")
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">{label}</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Hi <strong style="color:{_WHITE}">{_e(to_name)}</strong>,</p>
    <p style="margin:0 0 16px;color:{_MUTED}">
      You have a new message from <strong style="color:{_WHITE}">{_e(sender_name)}</strong>
      regarding <strong style="color:{_WHITE}">{_e(job_title)}</strong>.
    </p>
    <div style="background:{_CARD};border-left:4px solid {color};border-radius:0 8px 8px 0;
                padding:16px 18px;margin-bottom:16px">
      <p style="margin:0;color:{_WHITE};font-size:14px;line-height:1.7;white-space:pre-wrap">{_e(preview)}</p>
    </div>
    <p style="margin:0;color:{_MUTED};font-size:12px">
      Log in to reply and view your full conversation.
    </p>"""
    html = _wrap(body, f"{settings.FRONTEND_URL}/dashboard/candidate", "View Message →")
    _send_async(to_email, to_name, f"{label} – {job_title}", html, category="application_message")


def send_password_reset_email(to_email: str, name: str, reset_token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">Reset Your Password 🔐</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Hi <strong style="color:{_WHITE}">{_e(name)}</strong>,</p>
    <p style="margin:0 0 20px;color:{_MUTED}">
      We received a request to reset the password for your JobsNexGen account.
      Click the button below — this link is valid for <strong style="color:{_WHITE}">1 hour</strong>.
    </p>
    <div style="background:{_CARD};border-radius:8px;padding:14px 16px;
                border:1px solid rgba(255,255,255,.06);margin-bottom:16px">
      <p style="margin:0;color:{_MUTED};font-size:12px;word-break:break-all">{reset_url}</p>
    </div>
    <p style="margin:0;color:#475569;font-size:12px">
      If you did not request this reset, you can safely ignore this email.
      Your password will not change.
    </p>"""
    html = _wrap(body, reset_url, "Reset Password →")
    _send_async(to_email, name, "Reset your JobsNexGen password", html, category="password_reset")


# ── Contact form & newsletter ─────────────────────────────────────────────────

def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def _salary(lo: int | None, hi: int | None) -> str:
    """Same format as the website (lib/format.ts)."""
    def fmt(n: int) -> str:
        return f"₹{n / 100000:.1f}L" if n >= 100000 else f"₹{n:,}"
    if lo and hi:
        return f"{fmt(lo)} - {fmt(hi)}"
    if lo:
        return f"{fmt(lo)}+"
    return f"Up to {fmt(hi)}" if hi else ""


def send_contact_notification_email(enquiry_id: int, name: str, email: str, subject: str, message: str) -> None:
    """Tell the team about a new contact-form enquiry."""
    reply = f"mailto:{email}?subject=Re: {_one_line(subject)}"
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">New website enquiry 📩</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Someone filled in the contact form on jobsnexgen.com.</p>
    <table cellpadding="0" cellspacing="0" style="margin-bottom:16px;font-size:14px">
      <tr><td style="color:{_MUTED};padding:3px 16px 3px 0">From</td>
          <td style="color:{_WHITE};font-weight:600">{_e(name)}</td></tr>
      <tr><td style="color:{_MUTED};padding:3px 16px 3px 0">Email</td>
          <td><a href="{_e(reply)}" style="color:{_BLUE};text-decoration:none">{_e(email)}</a></td></tr>
      <tr><td style="color:{_MUTED};padding:3px 16px 3px 0">Subject</td>
          <td style="color:{_WHITE}">{_e(subject)}</td></tr>
      <tr><td style="color:{_MUTED};padding:3px 16px 3px 0">Reference</td>
          <td style="color:{_WHITE}">#{enquiry_id}</td></tr>
    </table>
    <div style="background:{_CARD};border-left:4px solid {_BLUE};border-radius:0 8px 8px 0;
                padding:16px 18px;margin-bottom:16px">
      <p style="margin:0;color:{_WHITE};font-size:14px;line-height:1.7;white-space:pre-wrap">{_e(message)}</p>
    </div>
    <p style="margin:0;color:{_MUTED};font-size:12px">
      Click the email address to reply. Mark it handled in the admin dashboard → Enquiries.
    </p>"""
    html = _wrap(body, f"{settings.FRONTEND_URL}/dashboard/admin", "Open Admin Dashboard →",
                 footer_note="Sent by the contact form on jobsnexgen.com.")
    _send_async(settings.CONTACT_INBOX, "JobsNexGen Team", f"New enquiry: {_one_line(subject)[:150]}", html,
                category="contact_enquiry")


def send_newsletter_confirm_email(to_email: str, confirm_url: str, unsubscribe_url: str) -> None:
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">Confirm your job alerts ✉️</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">
      Thanks for signing up for weekly job alerts from JobsNexGen. Click the button below to confirm
      your email address. Every Monday we'll send you the newest jobs posted on the site.
    </p>
    <p style="margin:0;color:#475569;font-size:12px">
      Didn't sign up? Just ignore this email and you won't hear from us again.
    </p>"""
    html = _wrap(body, confirm_url, "Confirm Subscription →",
                 footer_note=f'Someone entered this address on jobsnexgen.com. '
                             f'<a href="{_e(unsubscribe_url)}" style="color:#475569">Unsubscribe</a>')
    _send_async(to_email, "", "Confirm your JobsNexGen job alerts", html, category="newsletter_confirm")


def build_digest_email(jobs: list[dict], unsubscribe_url: str) -> tuple[str, str]:
    """Weekly new-jobs email. Each job: title, company, location, employment_type, salary_min, salary_max, url."""
    cards = ""
    for j in jobs:
        meta = " · ".join(x for x in [j.get("company"), j.get("location"), j.get("employment_type"),
                                      _salary(j.get("salary_min"), j.get("salary_max"))] if x)
        cards += f"""
    <a href="{_e(j["url"])}" style="display:block;text-decoration:none;background:{_CARD};border-radius:8px;
       border:1px solid rgba(255,255,255,.06);padding:14px 16px;margin-bottom:10px">
      <div style="color:{_WHITE};font-size:15px;font-weight:700">{_e(j["title"])}</div>
      <div style="color:{_MUTED};font-size:12px;margin-top:4px">{_e(meta)}</div>
    </a>"""
    count = len(jobs)
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">This week's new jobs 🚀</h2>
    <p style="margin:0 0 18px;color:{_MUTED}">
      {count} new job{"s" if count != 1 else ""} posted on JobsNexGen in the last 7 days:
    </p>
    {cards}"""
    html = _wrap(body, f"{settings.FRONTEND_URL}/jobs", "See All Jobs →",
                 footer_note=f'You subscribed to weekly job alerts on jobsnexgen.com. '
                             f'<a href="{_e(unsubscribe_url)}" style="color:#475569">Unsubscribe</a>')
    return f"{count} new job{'s' if count != 1 else ''} on JobsNexGen this week", html


# ── Job approval ──────────────────────────────────────────────────────────────

def send_job_pending_email(to_email: str, admin_name: str, job_title: str, company: str,
                           poster_name: str, poster_email: str) -> None:
    body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">A job is waiting for approval</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Hi <strong style="color:{_WHITE}">{_e(admin_name)}</strong>,</p>
    <p style="margin:0 0 16px;color:{_MUTED}">
      <strong style="color:{_WHITE}">{_e(poster_name)}</strong> ({_e(poster_email)}) posted
      <strong style="color:{_WHITE}">{_e(job_title)}</strong>{f" for {_e(company)}" if company else ""}.
      It stays hidden from candidates until you approve it.
    </p>"""
    html = _wrap(body, f"{settings.FRONTEND_URL}/dashboard/admin", "Review Jobs →")
    _send_async(to_email, admin_name, f"Approve job: {_one_line(job_title)[:120]}", html, category="job_pending")


def send_job_review_email(to_email: str, name: str, job_id: int, job_title: str, approved: bool,
                          reason: str | None) -> None:
    if approved:
        body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">Your job is live ✅</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Hi <strong style="color:{_WHITE}">{_e(name)}</strong>,</p>
    <p style="margin:0 0 16px;color:{_MUTED}">
      <strong style="color:{_WHITE}">{_e(job_title)}</strong> was approved and candidates can now see it and apply.
    </p>"""
        html = _wrap(body, f"{settings.FRONTEND_URL}/jobs/{job_id}", "View Job →")
        subject = f"Approved: {_one_line(job_title)[:120]}"
    else:
        body = f"""
    <h2 style="margin:0 0 8px;color:{_WHITE};font-size:22px">Your job needs changes</h2>
    <p style="margin:0 0 16px;color:{_MUTED}">Hi <strong style="color:{_WHITE}">{_e(name)}</strong>,</p>
    <p style="margin:0 0 16px;color:{_MUTED}">
      <strong style="color:{_WHITE}">{_e(job_title)}</strong> wasn't approved. Reason from the JobsNexGen team:
    </p>
    <div style="background:{_CARD};border-left:4px solid #F59E0B;border-radius:0 8px 8px 0;
                padding:14px 16px;margin-bottom:16px">
      <p style="margin:0;color:{_WHITE};font-size:14px;line-height:1.7;white-space:pre-wrap">{_e(reason)}</p>
    </div>
    <p style="margin:0;color:{_MUTED};font-size:13px">Edit the job from your dashboard and it goes back for review.</p>"""
        html = _wrap(body, f"{settings.FRONTEND_URL}/dashboard/recruiter", "Edit Job →")
        subject = f"Changes needed: {_one_line(job_title)[:120]}"
    _send_async(to_email, name, subject, html, category="job_review")

