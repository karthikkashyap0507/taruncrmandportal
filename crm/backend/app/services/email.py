import smtplib
import html as _html
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465
SMTP_USER = "bdm@jobsnexgen.com"
SMTP_PASS = "Jobsnexgen@2026"
FROM_NAME = "JobsNexGen CRM"
BRAND_COLOR = "#7C3AED"
FRONTEND_URL = "https://crm.jobsnexgen.com"


def _e(value) -> str:
    """HTML-escape user-supplied text before it goes into an email body."""
    return _html.escape(str(value if value is not None else ""))


def _fmt(dt) -> str:
    return dt.strftime("%d %b %Y, %I:%M %p") if dt else "-"


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
        <span style="color:#fff;font-size:22px;font-weight:700;">JobsNexGen</span>
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


def send_raw(to: str, to_name: str, subject: str, html: str) -> tuple[bool, str | None]:
    """One delivery attempt. Returns (ok, error). Used by the outbox, which retries."""
    if settings.EMAIL_BACKEND == "console":
        logger.info(f"[EMAIL:console] '{subject}' -> {to}")
        return True, None
    if settings.EMAIL_BACKEND == "fail":  # used by the QA suite to exercise retries
        return False, "simulated delivery failure (EMAIL_BACKEND=fail)"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"] = f"{to_name} <{to}>" if to_name else to
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to], msg.as_string())
        logger.info(f"Email sent to {to}: {subject}")
        return True, None
    except Exception as e:
        logger.error(f"Email failed to {to}: {e}")
        return False, f"{type(e).__name__}: {e}"


def _send_async(to: str, subject: str, html: str, category: str = "general", to_name: str = ""):
    """Queue in the outbox; sent in the background and retried on failure."""
    if not to:
        return
    from app.services.outbox import enqueue_email
    try:
        enqueue_email(category, to, to_name, subject, html)
    except Exception:
        logger.exception(f"could not queue email '{subject}' -> {to}")


def _p(text_html: str) -> str:
    return f'<p style="color:#374151;line-height:1.6;">{text_html}</p>'


# ── Public functions ───────────────────────────────────────────────────────────

def send_notification_email(to: str, name: str, title: str, body: str, url: str = None,
                            category: str = "notification"):
    """Generic email twin of an in-app notification."""
    html = _wrap(f'<h2 style="color:#111;margin:0 0 16px">{_e(title)}</h2>'
                 + _p(f"Hi {_e(name)},") + _p(_e(body)),
                 f"{FRONTEND_URL}{url}" if url else None, "Open in CRM" if url else None)
    _send_async(to, title, html, category, name)


def send_welcome_email(to: str, name: str):
    body = (f'<h2 style="color:#111;margin:0 0 16px">Welcome to JobsNexGen CRM, {_e(name)}!</h2>'
            + _p("Your account has been created. You can now log in and start managing leads, "
                 "candidates, and clients from your CRM dashboard.")
            + _p("If you have any questions, reach out to your administrator."))
    _send_async(to, "Welcome to JobsNexGen CRM", _wrap(body, f"{FRONTEND_URL}/login", "Go to CRM Dashboard"),
                "welcome", name)


def send_password_reset_email(to: str, name: str, token: str):
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    body = ('<h2 style="color:#111;margin:0 0 16px">Reset Your Password</h2>'
            + _p(f"Hi {_e(name)},")
            + _p("A password reset was requested for your account. Click the button below to set a new "
                 "password. This link expires in 1 hour.")
            + _p("If you didn't request this, you can safely ignore this email."))
    _send_async(to, "CRM Password Reset Request", _wrap(body, reset_url, "Reset Password"), "password_reset", name)


def send_lead_assigned_email(to: str, assignee_name: str, lead_company: str, lead_id: int):
    body = ('<h2 style="color:#111;margin:0 0 16px">Lead Assigned to You</h2>'
            + _p(f"Hi {_e(assignee_name)},")
            + _p(f"A new lead from <strong>{_e(lead_company)}</strong> has been assigned to you. "
                 "Please review the details and take appropriate action."))
    _send_async(to, f"New Lead Assigned: {lead_company}",
                _wrap(body, f"{FRONTEND_URL}/leads/{lead_id}", "View Lead"), "lead_assigned", assignee_name)


def send_task_assigned_email(to: str, name: str, title: str, due_date=None):
    due = f" It is due on <strong>{_fmt(due_date)}</strong>." if due_date else ""
    body = ('<h2 style="color:#111;margin:0 0 16px">New Task Assigned</h2>'
            + _p(f"Hi {_e(name)},") + _p(f"You have been assigned the task <strong>{_e(title)}</strong>.{due}"))
    _send_async(to, f"Task assigned: {title}", _wrap(body, f"{FRONTEND_URL}/tasks", "View Tasks"),
                "task_assigned", name)


def send_interview_scheduled_email(to: str, candidate_name: str, interview, job_title: str = None):
    where = (_p(f"<strong>Location/Link:</strong> {_e(interview.location_or_link)}")
             if interview.location_or_link else "")
    role = f" for <strong>{_e(job_title)}</strong>" if job_title else ""
    body = ('<h2 style="color:#111;margin:0 0 16px">Interview Scheduled</h2>'
            + _p(f"Dear {_e(candidate_name)},")
            + _p(f"Your interview{role} has been scheduled for <strong>{_fmt(interview.scheduled_at)}</strong> "
                 f"({interview.duration_minutes} minutes).")
            + where + _p("Please be available on time. Good luck!"))
    _send_async(to, "Your Interview is Scheduled - JobsNexGen", _wrap(body), "interview_scheduled", candidate_name)


def send_interview_updated_email(to: str, candidate_name: str, interview, change: str):
    """change: 'rescheduled' | 'cancelled'"""
    if change == "cancelled":
        msg = "Your interview has been <strong>cancelled</strong>. Our team will contact you about next steps."
        subject = "Interview Cancelled - JobsNexGen"
    else:
        msg = f"Your interview has been <strong>rescheduled</strong> to <strong>{_fmt(interview.scheduled_at)}</strong>."
        subject = "Interview Rescheduled - JobsNexGen"
    body = ('<h2 style="color:#111;margin:0 0 16px">Interview Update</h2>'
            + _p(f"Dear {_e(candidate_name)},") + _p(msg))
    _send_async(to, subject, _wrap(body), f"interview_{change}", candidate_name)


def send_interview_reminder_email(to: str, candidate_name: str, interview):
    where = (_p(f"<strong>Location/Link:</strong> {_e(interview.location_or_link)}")
             if interview.location_or_link else "")
    body = ('<h2 style="color:#111;margin:0 0 16px">Interview Reminder</h2>'
            + _p(f"Dear {_e(candidate_name)},")
            + _p(f"This is a reminder of your interview on <strong>{_fmt(interview.scheduled_at)}</strong>.")
            + where)
    _send_async(to, "Reminder: Your interview is coming up", _wrap(body), "interview_reminder", candidate_name)


def send_followup_reminder_email(to: str, name: str, company: str, followup_type: str, scheduled_at: datetime):
    body = ('<h2 style="color:#111;margin:0 0 16px">Follow-up Reminder</h2>'
            + _p(f"Hi {_e(name)},")
            + _p(f"You have a <strong>{_e(followup_type)}</strong> follow-up with <strong>{_e(company)}</strong> "
                 f"scheduled for <strong>{_fmt(scheduled_at)}</strong>."))
    _send_async(to, f"Reminder: Follow-up with {company}", _wrap(body, f"{FRONTEND_URL}/leads", "Open CRM"),
                "followup_reminder", name)


def send_candidate_status_email(to: str, candidate_name: str, new_status: str, job_title: str = None):
    job_part = f" for the <strong>{_e(job_title)}</strong> role" if job_title else ""
    body = ('<h2 style="color:#111;margin:0 0 16px">Application Status Update</h2>'
            + _p(f"Dear {_e(candidate_name)},")
            + _p(f"Your application{job_part} has moved to <strong>{_e(new_status.replace('_', ' ').title())}</strong>.")
            + _p("Our team will be in touch with next steps shortly."))
    _send_async(to, "Application Status Update - JobsNexGen", _wrap(body), "candidate_update", candidate_name)


def send_joining_confirmation_email(to: str, candidate_name: str, company: str, job_title: str, joined_on):
    body = ('<h2 style="color:#111;margin:0 0 16px">Congratulations on Joining!</h2>'
            + _p(f"Dear {_e(candidate_name)},")
            + _p(f"We have recorded your joining as <strong>{_e(job_title)}</strong> at "
                 f"<strong>{_e(company)}</strong> on {_fmt(joined_on)}. We wish you every success!"))
    _send_async(to, "Congratulations on your new role - JobsNexGen", _wrap(body), "joining", candidate_name)


def send_joining_reminder_email(to: str, candidate_name: str, company: str, joining_date):
    body = ('<h2 style="color:#111;margin:0 0 16px">Joining Reminder</h2>'
            + _p(f"Dear {_e(candidate_name)},")
            + _p(f"This is a reminder that your joining date at <strong>{_e(company)}</strong> is "
                 f"<strong>{_fmt(joining_date)}</strong>. Please reach out to us if anything has changed."))
    _send_async(to, "Reminder: Your joining date is tomorrow", _wrap(body), "joining_reminder", candidate_name)


def send_client_joining_email(to: str, contact_name: str, candidate_name: str, job_title: str, joined_on):
    """Employer/client notification that a placed candidate has joined."""
    body = ('<h2 style="color:#111;margin:0 0 16px">Candidate Joined</h2>'
            + _p(f"Dear {_e(contact_name)},")
            + _p(f"This is to confirm that <strong>{_e(candidate_name)}</strong> has joined as "
                 f"<strong>{_e(job_title)}</strong> on {_fmt(joined_on)}. Thank you for partnering with JobsNexGen."))
    _send_async(to, f"Joining confirmed: {candidate_name}", _wrap(body), "client_joining", contact_name)


def send_client_invoice_email(to: str, contact_name: str, invoice_number: str, candidate_name: str,
                              total_amount: float, due_date):
    """Employer/client notification that an invoice has been raised."""
    body = ('<h2 style="color:#111;margin:0 0 16px">Invoice Raised</h2>'
            + _p(f"Dear {_e(contact_name)},")
            + _p(f"Invoice <strong>{_e(invoice_number)}</strong> for the placement of "
                 f"<strong>{_e(candidate_name)}</strong> has been raised for "
                 f"<strong>INR {total_amount:,.2f}</strong> (incl. GST), due on {_fmt(due_date)}.")
            + _p("Please contact us if you have any questions."))
    _send_async(to, f"Invoice {invoice_number} - JobsNexGen", _wrap(body), "client_invoice", contact_name)
