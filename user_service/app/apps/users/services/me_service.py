from ..models import User


def get_current_user(user_id):
    return User.objects.select_related('profile').get(id=user_id)