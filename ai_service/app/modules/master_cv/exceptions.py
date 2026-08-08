class S3UploadError(Exception):
    pass

class S3ObjectNotFoundError(Exception):
    pass

class FileTooLargeError(Exception):
    pass

class InvalidPDFError(Exception):
    pass

class CVStructuringError(Exception):
    pass