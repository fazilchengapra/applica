"""Composes the home aggregate from account state, local CV state and inbox state.

The three sources are fetched concurrently: the upstream calls are plain HTTP
and do not touch the shared AsyncSession, so overlapping them with the local
query is safe and keeps the endpoint at roughly one round trip instead of three.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.home import clients, repository
from app.modules.home.schemas import (
    AccountStepFlags,
    HomeOnboarding,
    HomeResponse,
    HomeStep,
    HomeStepLabel,
    OnboardingStepKey,
)

# display order for the onboarding checklist, paired with its label
STEP_LABELS: list[tuple[OnboardingStepKey, HomeStepLabel]] = [
    (OnboardingStepKey.verify_email, HomeStepLabel.verify_email),
    (OnboardingStepKey.verify_phone, HomeStepLabel.verify_phone),
    (OnboardingStepKey.add_photo, HomeStepLabel.add_photo),
    (OnboardingStepKey.complete_profile, HomeStepLabel.complete_profile),
    (OnboardingStepKey.upload_cv, HomeStepLabel.upload_cv),
]


def _build_onboarding(account_steps: AccountStepFlags, has_cv: bool) -> HomeOnboarding:
    """Assemble the five steps and derive the completeness percent.

    ``percent`` is the share of steps completed, rounded to the nearest whole
    percent. ``upload_cv`` is supplied by this service because the master CV
    lives in this database; the other four come from user_service.
    """
    done_by_key: dict[OnboardingStepKey, bool] = {
        OnboardingStepKey.verify_email: account_steps.verify_email,
        OnboardingStepKey.verify_phone: account_steps.verify_phone,
        OnboardingStepKey.add_photo: account_steps.add_photo,
        OnboardingStepKey.complete_profile: account_steps.complete_profile,
        OnboardingStepKey.upload_cv: has_cv,
    }

    steps = [
        HomeStep(key=key, label=label, done=done_by_key[key])
        for key, label in STEP_LABELS
    ]

    total = len(steps)
    completed = sum(1 for step in steps if step.done)

    return HomeOnboarding(
        percent=round(completed / total * 100) if total else 0,
        steps=steps,
    )


async def build_home(db: AsyncSession, user_id: int) -> HomeResponse:
    """Full home aggregate for one user.
    Fails loudly if either upstream is unavailable rather than rendering a
    half-empty home page: the account sections are the point of the endpoint,
    and a silently blank profile is worse for the user than a visible error.
    """
    account, has_cv, notifications = await asyncio.gather(
        clients.fetch_account(user_id),
        repository.has_uploaded_cv(db, user_id),
        clients.fetch_unread_count(user_id),
    )

    return HomeResponse(
        user=account.user,
        profile=account.profile,
        onboarding=_build_onboarding(account.account_steps, has_cv),
        notifications=notifications,
        linked_accounts=account.linked_accounts,
        generated_at=datetime.now(timezone.utc),
    )
