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

class CVNotfoundError(Exception):
    pass

class CVNotReadyError(Exception):
    pass

class CVInvalidParsedDataError(Exception):
    pass

class MultipleMasterCVError(Exception):
    pass