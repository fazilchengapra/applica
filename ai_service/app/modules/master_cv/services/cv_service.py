import magic
from pathlib import Path

# exceptions
from app.modules.master_cv.exceptions import InvalidPDFError, FileTooLargeError

# constants
from app.modules.master_cv.constants import MAX_FILE_SIZE_MB

# s3 service
from .s3_service import upload_pdf_to_s3


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


async def process_cv_upload(filename: str, contents: bytes) -> Path:
    validate_file_size(contents)
    validate_pdf(contents)
    object_key = upload_pdf_to_s3(contents, filename)

    return object_key
