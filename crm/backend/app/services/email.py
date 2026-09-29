import smtplib
import threading
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465
SMTP_USER = "bdm@jobsnexgen.com"
SMTP_PASS = "Jobsnexgen@2026"
FROM_NAME = "JobsNexGen CRM"
BRAND_COLOR = "#7C3AED"
FRONTEND_URL = "https://crm.jobsnexgen.com"


def _wrap(body_html: str, cta_url: str = None, cta_label: str = None) -> str:
    cta_block = ""
    if cta_url and cta_label:
        cta_block = f"""
        <div style="text-align:center;margin:30px 0;">
          <a href="{cta_url}" style="background:{BRAND_COLOR};color:#fff;padding:12px 28px;border-radius:6px;
             text-decoration:none;font-weight:600;font-size:15px;">{cta_label}</a>
        </div>"""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <tr><td style="background:{BRAND_COLOR};padding:24px 32px;">
        <span style="color:#fff;font-size:22px;font-weight:700;">JobsNexGen CRM</span>
      </td></tr>
      <tr><td style="padding:32px;">
        {body_html}
        {cta_block}
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:30px 0;">
        <p style="color:#9ca3af;font-size:12px;margin:0;">
          &copy; {datetime.now().year} JobsNexGen &mdash; This is an automated notification.
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


def _send(to: str, subject: str, html: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to], msg.as_string())
        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email failed to {to}: {e}")
        return False


def _send_async(to: str, subject: str, html: str):
    threading.Thread(target=_send, args=(to, subject, html), daemon=True).start()


# ── Public functions ───────────────────────────────────────────────────────────

def send_welcome_email(to: str, name: str):
    body = f"""
    <h2 style="color:#111;margin:0 0 16px">Welcome to JobsNexGen CRM, {name}!</h2>
    <p style="color:#374151;line-height:1.6;">
      Your account has been created. You can now log in and start managing leads,
      candidates, and clients from your CRM dashboard.
    </p>
    <p style="color:#374151;">If you have any questions, reach out to your administrator.</p>"""
    html = _wrap(body, f"{FRONTEND_URL}/login", "Go to CRM Dashboard")
    _send_async(to, "Welcome to JobsNexGen CRM", html)


def send_password_reset_email(to: str, name: str, token: str):
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    body = f"""
    <h2 style="color:#111;margin:0 0 16px">Reset Your Password</h2>
    <p style="color:#374151;line-height:1.6;">Hi {name},</p>
    <p style="color:#374151;line-height:1.6;">
      A password reset was requested for your account. Click the button below to set a new password.
      This link expires in 1 hour.
    </p>
    <p style="color:#374151;">If you didn't request this, you can safely ignore this email.</p>"""
    html = _wrap(body, reset_url, "Reset Password")
    _send_async(to, "CRM Password Reset Request", html)


def send_lead_assigned_email(to: str, assignee_name: str, lead_company: str, lead_id: int):
    body = f"""
    <h2 style="color:#111;margin:0 0 16px">Lead Assigned to You</h2>
    <p style="color:#374151;line-height:1.6;">Hi {assignee_name},</p>
    <p style="color:#374151;line-height:1.6;">
      A new lead from <strong>{lead_company}</strong> has been assigned to you.
      Please review the details and take appropriate action.
    </p>"""
    html = _wrap(body, f"{FRONTEND_URL}/leads/{lead_id}", "View Lead")
    _send_async(to, f"New Lead Assigned: {lead_company}", html)


def send_lead_status_changed_email(to: str, name: str, company: str, old_status: str, new_status: str, lead_id: int):
    body = f"""
    <h2 style="color:#111;margin:0 0 16px">Lead Status Updated</h2>
    <p style="color:#374151;line-height:1.6;">Hi {name},</p>
    <p style="color:#374151;line-height:1.6;">
      The lead for <strong>{company}</strong> has been updated from
      <strong>{old_status}</strong> to <strong>{new_status}</strong>.
    </p>"""
    html = _wrap(body, f"{FRONTEND_URL}/leads/{lead_id}", "View Lead")
    _send_async(to, f"Lead Updated: {company}", html)


def send_interview_scheduled_email(to: str, candidate_name: str, interview):
    scheduled = interview.scheduled_at.strftime("%B %d, %Y at %I:%M %p")
    body = f"""
    <h2 style="color:#111;margin:0 0 16px">Interview Scheduled</h2>
    <p style="color:#374151;line-height:1.6;">Dear {candidate_name},</p>
    <p style="color:#374151;line-height:1.6;">
      Your interview has been scheduled for <strong>{scheduled}</strong> ({interview.duration_minutes} minutes).
    </p>
    {"<p style='color:#374151;'><strong>Location/Link:</strong> " + interview.location_or_link + "</p>" if interview.location_or_link else ""}
    <p style="color:#374151;">Please be available on time. Good luck!</p>"""
    html = _wrap(body)
    _send_async(to, "Your Interview is Scheduled – JobsNexGen", html)


def send_followup_reminder_email(to: str, name: str, company: str, followup_type: str, scheduled_at: datetime):
    scheduled = scheduled_at.strftime("%B %d, %Y at %I:%M %p")
    body = f"""
    <h2 style="color:#111;margin:0 0 16px">Follow-up Reminder</h2>
    <p style="color:#374151;line-height:1.6;">Hi {name},</p>
    <p style="color:#374151;line-height:1.6;">
      You have a <strong>{followup_type}</strong> follow-up with <strong>{company}</strong>
      scheduled for <strong>{scheduled}</strong>.
    </p>"""
    html = _wrap(body, f"{FRONTEND_URL}/leads", "Open CRM")
    _send_async(to, f"Reminder: Follow-up with {company}", html)


def send_candidate_status_email(to: str, candidate_name: str, new_status: str, job_title: str = None):
    job_part = f" for the <strong>{job_title}</strong> role" if job_title else ""
    body = f"""
    <h2 style="color:#111;margin:0 0 16px">Application Status Update</h2>
    <p style="color:#374151;line-height:1.6;">Dear {candidate_name},</p>
    <p style="color:#374151;line-height:1.6;">
      Your application status{job_part} has been updated to <strong>{new_status}</strong>.
    </p>
    <p style="color:#374151;">Our team will be in touch with next steps shortly.</p>"""
    html = _wrap(body)
    _send_async(to, "Application Status Update – JobsNexGen", html)


def send_daily_report_reminder(to: str, name: str):
    body = f"""
    <h2 style="color:#111;margin:0 0 16px">Daily Report Reminder</h2>
    <p style="color:#374151;line-height:1.6;">Hi {name},</p>
    <p style="color:#374151;line-height:1.6;">
      Please submit your daily activity report for today before EOD.
    </p>"""
    html = _wrap(body, f"{FRONTEND_URL}/reports", "Submit Report")
    _send_async(to, "Reminder: Daily Report Due Today", html)
