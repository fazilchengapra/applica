from app.apps.profiles.exceptions import ProfileNotFound
from app.apps.profiles.models import Profile


def update_profile(user_id, data):
    try:
        profile = Profile.objects.get(user_id=user_id)
    except Profile.DoesNotExist as exc:
        raise ProfileNotFound("Profile not found!") from exc

    allowed_fields = {
        "first_name",
        "last_name",
        "display_name",
        "bio",
        "date_of_birth",
        "gender",
        "country",
        "city",
        "timezone",
        "locale",
    }

    for field, value in data.items():
        if field in allowed_fields:
            setattr(profile, field, value)

    profile.save()
    return profile
