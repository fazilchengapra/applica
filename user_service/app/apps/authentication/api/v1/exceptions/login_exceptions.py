class InvalidCredentialsError(Exception):
    pass


class AccountInactiveError(Exception):
    pass


class LoginLockedError(Exception):
    pass