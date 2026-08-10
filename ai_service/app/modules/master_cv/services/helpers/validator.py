import magic
from app.modules.master_cv.exceptions import InvalidPDFError, FileTooLargeError
from app.modules.master_cv.constants import MAX_FILE_SIZE_MB


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
