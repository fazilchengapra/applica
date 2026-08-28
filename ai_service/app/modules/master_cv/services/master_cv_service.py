from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.master_cv.repository.master_cv_repo import get_master_cv
from app.modules.master_cv.exceptions import MultipleMasterCVError


async def if_master_cv_exist(user_id: int, session: AsyncSession):
    master_cv = await get_master_cv(user_id=user_id, session=session)

    if master_cv:
        raise MultipleMasterCVError("Cannot do the multiple master cv upload")
