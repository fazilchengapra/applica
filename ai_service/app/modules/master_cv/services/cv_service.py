from fastapi import Depends
import magic
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

# model
from app.modules.master_cv.models import MasterCV

# exceptions
from app.modules.master_cv.exceptions import InvalidPDFError, FileTooLargeError

# constants
from app.modules.master_cv.constants import MAX_FILE_SIZE_MB

# s3 service
from .s3_service import upload_pdf_to_s3, delete_pdf_from_s3, _pdf_exists

# services
from .helpers.text_extractor import extract_pdf
from .helpers.cv_structor import structure_cv_text

# tasks
from ..tasks import process_cv_task


# helper services :-
def validate_file_size(contents: bytes) -> None:
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise FileTooLargeError(
            f"File size {size_mb:.2f}MB exceeds the {MAX_FILE_SIZE_MB}MB limit"
        )


def validate_pdf(contents: bytes) -> None:
    mime = magic.from_buffer(contents, mime=True)
    if mime != "application/pdf":
        raise InvalidPDFError("Only PDF files are allowed")


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
    old_object_key: str, filename: str, contents: bytes
) -> Path:
    validate_file_size(contents)
    validate_pdf(contents)
    _pdf_exists(old_object_key)
    new_object_key = upload_pdf_to_s3(contents, filename)

    delete_pdf_from_s3(old_object_key)

    return new_object_key