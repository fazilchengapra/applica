from fastapi import Depends
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
import uuid

# model
from app.modules.master_cv.models.master_cv import MasterCV, MasterCVVersion, CVStatus

# s3 service
from .s3_service import upload_pdf_to_s3

from .helpers.validator import validate_file_size, validate_pdf

# tasks
from ..tasks import process_cv_task

# exceptions
from ..exceptions import CVNotfoundError


# main services :-
async def process_cv_upload(
    filename: str,
    contents: bytes,
    user_id: str,
    session: AsyncSession,
    target_role: str,
) -> uuid.UUID:
    validate_file_size(contents)
    validate_pdf(contents)
    object_key = upload_pdf_to_s3(contents, filename)

    cv_record = MasterCV(
        user_id=user_id,
    )

    session.add(cv_record)

    # get cv_record.id without committing
    await session.flush()

    version_record = MasterCVVersion(
        master_cv_id=cv_record.id,
        version=1,
        is_current=True,
        s3_key=object_key,
        status=CVStatus.PENDING,
        target_role=target_role,
    )

    session.add(version_record)

    await session.commit()
    await session.refresh(cv_record)
    await session.refresh(version_record)

    print(f"cv  version id is: ${version_record.id} s3_key is {version_record.s3_key}")
    process_cv_task.delay(
        str(version_record.id), str(version_record.s3_key), str(user_id)
    )
    return version_record.id


async def process_cv_update(
    filename: str,
    contents: bytes,
    master_cv_id: uuid.UUID,
    user_id: str,
    session: AsyncSession,
) -> Path:
    master_cv_record = await session.scalar(
        select(MasterCV).where(MasterCV.id == master_cv_id, MasterCV.user_id == user_id)
    )
    print("master_cv_record: ", master_cv_record)
    if not master_cv_record:
        raise CVNotfoundError("CV not found")

    cv_version_record = await session.scalar(
        select(MasterCVVersion).where(
            MasterCVVersion.master_cv_id == master_cv_record.id,
            MasterCVVersion.is_current.is_(True),
        )
    )

    if not cv_version_record:
        raise CVNotfoundError("CV not found")

    cv_version_record.is_current = False

    session.add(cv_version_record)

    validate_file_size(contents)
    validate_pdf(contents)

    new_object_key = upload_pdf_to_s3(contents, filename)

    new_version_record = MasterCVVersion(
        master_cv_id=master_cv_id,
        version=cv_version_record.version + 1,
        is_current=True,
        s3_key=new_object_key,
        status=CVStatus.PENDING,
    )

    session.add(new_version_record)

    await session.commit()
    await session.refresh(cv_version_record)
    await session.refresh(new_version_record)

    process_cv_task.delay(str(new_version_record.id), str(new_version_record.s3_key))
    return new_version_record.id
