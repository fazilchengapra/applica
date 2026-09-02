from enum import Enum

from pydantic import BaseModel, EmailStr


class RegistrationMethod(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"
    PHONE_OTP = "phone"


class AccountRegisteredPayload(BaseModel):
    email: EmailStr
    display_name: str
    registration_method: RegistrationMethod


class AccountVerificationPayload(BaseModel):
    email: EmailStr
    verification_link: str


class EmailChangedPayload(BaseModel):
    email: EmailStr
    old_email: str # it's masked email
