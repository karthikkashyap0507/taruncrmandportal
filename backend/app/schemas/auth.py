from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.candidate
    company_name: str | None = Field(
        default=None,
        max_length=255,
        description="Required for recruiter and company_admin",
    )

    @field_validator("role")
    @classmethod
    def no_self_serve_platform_admin(cls, v: UserRole) -> UserRole:
        if v == UserRole.platform_admin:
            raise ValueError("Cannot register as platform admin")
        return v

    @field_validator("company_name")
    @classmethod
    def strip_company(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s if s else None

    @model_validator(mode="after")
    def require_company_for_employers(self):
        if self.role in (UserRole.recruiter, UserRole.company_admin):
            if not self.company_name:
                raise ValueError("Company name is required for recruiter and company admin accounts")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole

    model_config = {"from_attributes": True}


class AuthSuccessResponse(TokenResponse):
    user: UserResponse
