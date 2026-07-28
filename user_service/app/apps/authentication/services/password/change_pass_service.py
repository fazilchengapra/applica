from app.apps.notifications.services.password_notification import password_change_notification

def change_password(user, old_password: str, new_password: str) -> None:
    if not user.check_password(old_password):
        raise ValueError("Current password is incorrect.")

    if old_password == new_password:
        raise ValueError("New password must be different from the current password.")

    user.set_password(new_password)
    user.save(update_fields=["password"])

    password_change_notification(user=user)