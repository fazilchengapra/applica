class EmailAlreadyVerifiedError(Exception):
    pass


class EmailVerificationInvalidError(Exception):
    pass


class EmailNotVerifiedError(Exception):
    pass

class EmailInActiveError(Exception):
    pass