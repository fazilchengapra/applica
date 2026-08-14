from app.apps.notifications.services.create_and_push_notification import create_and_push
from app.apps.notifications.constants.notification_type import NotificationType

# mask the phone number
from app.apps.common.utils.mask import mask_phone_number


def phone_number_change_notification_helper(*, user, new_phone, old_phone):

    metadata = {
        "new_phone": mask_phone_number(new_phone),
        "old_phone": mask_phone_number(old_phone),
        "changed_via": "user_initiated",
    }

    return {
        "user": user,
        "event": NotificationType.PHONE_CHANGED,
        "title": "Phone Number Changed Successfully!",
        "body": "Your account phone number has been changed successfully.",
        "metadata": metadata,
    }


def phone_verified_notification_helper(*, user, phone):
    metadata = {
        "email": mask_phone_number(phone),
        "verification_method": "otp",
    }

    return {
        "user": user,
        "event": NotificationType.PHONE_VERIFIED,
        "title": "Phone Number Verified Success!",
        "body": "Your Phone number has been verified successfully.",
        "metadata": metadata,
    }
