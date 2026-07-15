from app.apps.profiles.models import Profile
from app.apps.profiles.exceptions import ProfileNotFound


def get_profile(user_id):
    try:
        profile = Profile.objects.get(user=user_id)

    except Profile.DoesNotExist:
        raise ProfileNotFound('Profile not found!')
    
    return profile