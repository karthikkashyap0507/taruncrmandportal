"""
Create a platform admin user (not available via public registration).

Usage (from repo root, with venv activated and DATABASE_URL set):

  cd backend
  python -m scripts.seed_platform_admin

Environment variables:
  ADMIN_EMAIL   default admin@jobsnexgen.in
  ADMIN_PASSWORD default (change immediately): ChangeMe123!
  ADMIN_NAME    default Platform Admin
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.core.database import SessionLocal
from app.models.user import User, UserRole


def main() -> None:
    email = os.environ.get("ADMIN_EMAIL", "admin@jobsnexgen.in").lower()
    password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
    name = os.environ.get("ADMIN_NAME", "Platform Admin")

    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.role != UserRole.platform_admin:
                existing.role = UserRole.platform_admin
                existing.password_hash = hash_password(password)
                existing.name = name
                db.commit()
                print(f"Updated existing user {email} to platform_admin.")
            else:
                print(f"User {email} already exists as platform_admin.")
            return

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.platform_admin,
        )
        db.add(user)
        db.commit()
        print(f"Created platform admin: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
