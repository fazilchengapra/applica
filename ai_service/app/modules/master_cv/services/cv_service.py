from fastapi import Depends
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from datetime import datetime, timezone
import uuid

# model
from app.modules.master_cv.models import MasterCV

# s3 service
from .s3_service import upload_pdf_to_s3, delete_pdf_from_s3, _pdf_exists

# services
from .helpers.text_extractor import extract_pdf
from .helpers.cv_structor import structure_cv_text

from .helpers.validator import validate_file_size, validate_pdf

# tasks
from ..tasks import process_cv_task

# exceptions
from ..exceptions import CVNotfoundError


async def soft_delete(session: AsyncSession, cv_id: str, user_id: str) -> None:
    cv_record = await session.get(MasterCV, cv_id)

    if cv_record is None or cv_record.deleted_at is not None:
        raise CVNotfoundError("can't find any cv")

    if str(cv_record.user_id) != str(user_id):
        raise CVNotfoundError("can't find any cv")

    cv_record.is_deleted = True
    cv_record.deleted_at = datetime.now(timezone.utc)

    await session.commit()


# main services :-
async def process_cv_upload(
    filename: str,
    contents: bytes,
    user_id: str,
    session: AsyncSession,
) -> Path:
    validate_file_size(contents)
    validate_pdf(contents)
    object_key = upload_pdf_to_s3(contents, filename)

    cv_record = MasterCV(
        user_id=user_id,
        s3_key=object_key,
    )

    session.add(cv_record)

    await session.commit()
    await session.refresh(cv_record)

    print(f"cv id is: ${cv_record.id} s3_key is {cv_record.s3_key}")
    process_cv_task.delay(str(cv_record.id), str(cv_record.s3_key))
    return object_key


async def process_cv_update(
    filename: str,
    contents: bytes,
    cv_id: uuid.UUID,
    user_id: str,
    session: AsyncSession,
) -> Path:
    validate_file_size(contents)
    validate_pdf(contents)

    print("user_id", user_id, "master_cv", cv_id)

    await soft_delete(session, cv_id, user_id)
    new_object_key = upload_pdf_to_s3(contents, filename)

    return new_object_key
