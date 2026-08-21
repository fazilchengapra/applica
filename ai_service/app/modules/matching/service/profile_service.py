from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.matching.schemas.user_profile import UserProfile
from app.modules.matching.exceptions import UserProfileNotFoundError
from app.modules.matching.repositories.profile_repository import (
    get_current_completed_cv,
)


async def get_user_profile(
    db: AsyncSession,
    user_id: int,
) -> UserProfile:

    cv = await get_current_completed_cv(
        db=db,
        user_id=user_id,
    )

    if cv is None:
        raise UserProfileNotFoundError(
            f"No completed current CV found for user {user_id}"
        )

    return UserProfile(
        user_id=user_id, target_role=cv.target_role, cv_embedding=cv.embedding
    )
