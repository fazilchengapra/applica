from app.apps.notifications.services.create_and_push_notification import create_and_push
from app.apps.notifications.constants.notification_type import NotificationType

# mask the mail
from app.apps.common.utils.mask import mask_email


def email_change_notification_helper(*, user, new_email, old_email):

    metadata = {
        "new_email": mask_email(new_email),
        "old_email": mask_email(old_email),
        "changed_via": "user_initiated",
    }

    return {
        "event": NotificationType.EMAIL_CHANGED,
        "user_id": str(user.id),
        "title": "Email Changed Successfully!",
        "body": "Your account email address is changed successfully",
        "meta_data": metadata,
    }


def email_verified_notification(*, user, email):
    metadata = {
        "email": mask_email(email),
        "verification_method": "link",
    }

    return create_and_push(
        user=user,
        type=NotificationType.EMAIL_VERIFIED,
        title="Email Verified Success!",
        body="Your email has been verified success fully.",
        metadata=metadata,
    )
