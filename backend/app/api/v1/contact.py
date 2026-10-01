"""Public contact form and newsletter sign-up (no login needed)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ratelimit import client_ip, contact_ip_limiter, newsletter_email_limiter, newsletter_ip_limiter
from app.models.enquiry import ContactMessage, NewsletterSubscriber
from app.services import newsletter
from app.services.email import send_contact_notification_email, send_newsletter_confirm_email

router = APIRouter(tags=["contact"])


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=10, max_length=5000)

    @field_validator("name", "subject", mode="before")
    @classmethod
    def _single_line(cls, v):
        return " ".join(v.split()) if isinstance(v, str) else v

    @field_validator("message", mode="before")
    @classmethod
    def _trim(cls, v):
        return v.strip() if isinstance(v, str) else v


class SubscribeIn(BaseModel):
    email: EmailStr


class SignedLinkIn(BaseModel):
    email: EmailStr
    sig: str = Field(min_length=1, max_length=128)


@router.post("/contact", status_code=201)
def submit_contact(payload: ContactCreate, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    contact_ip_limiter.check(ip, "You've sent several messages already. Please try again in an hour, "
                                 "or email us directly.")
    row = ContactMessage(name=payload.name, email=payload.email.lower(), subject=payload.subject,
                         message=payload.message, ip_address=ip, status="new")
    db.add(row)
    db.commit()
    send_contact_notification_email(row.id, row.name, row.email, row.subject, row.message)
    return {"id": row.id, "message": "Thanks! Your message has been sent. We'll get back to you within 48 hours."}


@router.post("/newsletter/subscribe")
def subscribe(payload: SubscribeIn, request: Request, db: Session = Depends(get_db)):
    newsletter_ip_limiter.check(client_ip(request), "Too many sign-ups from your network. Please try again later.")
    email = payload.email.lower()
    sub = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email).first()
    if sub is None:
        sub = NewsletterSubscriber(email=email)
        db.add(sub)
        try:
            db.commit()
        except IntegrityError:  # two sign-ups for the same address at once
            db.rollback()
            sub = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email).one()
    elif sub.unsubscribed_at is not None:
        sub.unsubscribed_at = None
        sub.confirmed_at = None  # coming back needs a fresh confirmation
        db.commit()

    if sub.confirmed_at is not None:
        return {"status": "subscribed", "message": "You're already subscribed to weekly job alerts."}
    newsletter_email_limiter.check(email, "We've already sent a confirmation link to this address. "
                                          "Please check your inbox (and spam folder).")
    send_newsletter_confirm_email(email, newsletter.link("confirm", email), newsletter.link("unsubscribe", email))
    return {"status": "pending",
            "message": "Almost done! We've emailed you a link — click it to confirm your subscription."}


@router.post("/newsletter/confirm")
def confirm_subscription(payload: SignedLinkIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if not newsletter.verify("confirm", email, payload.sig):
        raise HTTPException(status_code=400, detail="This confirmation link is invalid. Please subscribe again.")
    sub = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email).first()
    if not sub or sub.unsubscribed_at is not None:
        raise HTTPException(status_code=404, detail="This subscription was cancelled. Please subscribe again.")
    if sub.confirmed_at is None:
        sub.confirmed_at = datetime.now(timezone.utc)
        db.commit()
    return {"message": "Subscription confirmed! Your first job alert arrives next Monday."}


@router.post("/newsletter/unsubscribe")
def unsubscribe(payload: SignedLinkIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if not newsletter.verify("unsubscribe", email, payload.sig):
        raise HTTPException(status_code=400, detail="This unsubscribe link is invalid.")
    sub = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email).first()
    if sub and sub.unsubscribed_at is None:
        sub.unsubscribed_at = datetime.now(timezone.utc)
        db.commit()
    return {"message": "You've been unsubscribed and won't receive any more job alerts."}
