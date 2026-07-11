class PhoneInActivationError(Exception):
    pass


class PhoneAlreadyVerifiedError(Exception):
    pass


class PhoneNotVerifiedError(Exception):
    pass

class PhoneChangeInvalidError(Exception):
    pass


class PhoneNumberInUseError(Exception):
    pass


class SamePhoneNumberError(Exception):
    pass