class EmailAlreadyVerifiedError(Exception):
    pass


class EmailVerificationInvalidError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AccountInactiveError(Exception):
    pass


class LoginLockedError(Exception):
    pass


class PhoneInActivationError:
    pass


class PhoneAlreadyVerifiedError(Exception):
    pass


class PhoneNotVerifiedError(Exception):
    pass


class EmailInActiveError(Exception):
    pass


# otp
class OTPCooldownError(Exception):
    pass


class OTPLockedError(Exception):
    pass


class OTPInvalidError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class PhoneChangeInvalidError(Exception):
    pass

class PhoneNumberInUseError(Exception):
    pass

class SamePhoneNumberError(Exception):
    pass