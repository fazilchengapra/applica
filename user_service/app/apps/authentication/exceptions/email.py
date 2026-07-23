class EmailAlreadyVerifiedError(Exception):
    pass


class EmailVerificationInvalidError(Exception):
    pass

class EmailNotVerifiedError(Exception):
    pass

class EmailInActiveError(Exception):
    pass

class EmailInUseError(Exception):
    pass

class EmailChangeInvalidError(Exception):
    pass

class SameEmailError(Exception):
    pass

class EmailChangeTokenInvalidError(Exception):
    pass