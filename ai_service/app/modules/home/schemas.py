"""Response schemas for the composed home aggregate.

The home payload spans two services: account state lives in user_service and CV
state lives here in ai_service. This module owns the *public* contract, plus the
narrow input schemas used to validate user_service's reply, so an upstream
shape change surfaces as a validation error here rather than a malformed home
page in the client.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OnboardingStepKey(str, Enum):
    """The five onboarding steps, in the order the client should render them.

    The order is display order and is part of the contract, so it is expressed
    as an enum rather than assembled from a dict.
    """

    verify_email = "verify_email"
    verify_phone = "verify_phone"
    add_photo = "add_photo"
    complete_profile = "complete_profile"
    upload_cv = "upload_cv"


class HomeStepLabel(str, Enum):
    verify_email = "Verify your email"
    verify_phone = "Verify your phone"
    add_photo = "Add a profile photo"
    complete_profile = "Complete your profile"
    upload_cv = "Upload your resume"


class HomeUser(BaseModel):
    id: int
    email: str
    phone_number: str | None = None
    is_email_verified: bool
    is_phone_verified: bool
    date_joined: datetime
    last_login: datetime | None = None
    is_staff: bool
    roles: list[str] = Field(default_factory=list)


class HomeProfile(BaseModel):
    display_name: str = ""
    avatar_url: str = ""
    bio: str = ""
    country: str = ""
    city: str = ""
    timezone: str = ""
    locale: str = ""


class HomeStep(BaseModel):
    key: OnboardingStepKey
    label: HomeStepLabel
    done: bool


class HomeOnboarding(BaseModel):
    percent: int = Field(ge=0, le=100)
    steps: list[HomeStep]


class HomeNotifications(BaseModel):
    unread: int = 0


class UnreadCountPayload(BaseModel):
    """Wire shape of notification_service's internal unread-count reply.

    Separate from :class:`HomeNotifications` because it validates an *upstream*
    response, and every field here is required with unknown keys rejected. Sharing
    the public model would let a renamed or mistyped field validate against its
    default and silently report a wrong count — the one field in the home
    aggregate that has no other source to cross-check against.
    """

    model_config = ConfigDict(extra="forbid")

    unread: int = Field(ge=0)


class HomeLinkedAccount(BaseModel):
    provider: str
    is_verified: bool
    is_active: bool
    linked_at: datetime


class HomeResponse(BaseModel):
    user: HomeUser
    profile: HomeProfile
    onboarding: HomeOnboarding
    notifications: HomeNotifications
    linked_accounts: list[HomeLinkedAccount] = Field(default_factory=list)
    generated_at: datetime


# --- user_service wire format -------------------------------------------------
# Mirrors HomeUser/HomeProfile/etc. but as *input* models, kept separate so a
# field can be widened for transport without changing the public response.


class AccountStepFlags(BaseModel):
    """The four steps user_service evaluates; upload_cv is computed here."""

    verify_email: bool = False
    verify_phone: bool = False
    add_photo: bool = False
    complete_profile: bool = False


class AccountPayload(BaseModel):
    user: HomeUser
    profile: HomeProfile = HomeProfile()
    account_steps: AccountStepFlags = AccountStepFlags()
    linked_accounts: list[HomeLinkedAccount] = Field(default_factory=list)
