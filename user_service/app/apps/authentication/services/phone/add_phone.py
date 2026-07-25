from django.db import transaction
from app.apps.users.models import User
from app.apps.authentication.models.auth_method import AuthMethod

# exception
from app.apps.authentication.exceptions.phone import (
    PhoneAlreadyVerifiedError,
    PhoneNumberInUseError,
    SamePhoneNumberError
)


@transaction.atomic
def add_phone_number(user, phone_number):

    if user.phone_number and user.is_phone_verified:
        raise PhoneAlreadyVerifiedError("Your Phone num ber is already verified, you can't do this action!")

    if user.phone_number == phone_number:
        raise SamePhoneNumberError('Use different phone number')

    if_users_in = User.objects.filter(phone_number=phone_number).first()

    if if_users_in:
        raise PhoneNumberInUseError("This phone number is used another user")

    user.phone_number = phone_number
    user.is_phone_verified = False

    user.save(update_fields=["phone_number", "is_phone_verified"])

    # checking the account is have a same auth method record
    if_in_auth_method = AuthMethod.objects.filter(
        user=user, provider=AuthMethod.MOBILE
    ).first()

    # if not auth method for this provider just create if have skip
    if not if_in_auth_method:
        AuthMethod.objects.create(user=user, provider=AuthMethod.MOBILE)

    return user
