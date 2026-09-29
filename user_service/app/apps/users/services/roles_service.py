"""Single source of truth for a user's role list.

Roles are not persisted: they are derived from the user's flags every time they
authenticate and embedded in the JWT. Login, Google OAuth and the home
aggregate all read from here so the token claim, the login response and
``GET /api/v1/users/me/home`` can never disagree about a user's roles.
"""

BASE_ROLE = "user"
STAFF_ROLE = "staff"
ADMIN_ROLE = "admin"


def get_user_roles(user) -> list[str]:
    """Return the ordered role list for ``user``.

    Order is stable and least- to most-privileged so clients can rely on it:
    every user has ``user``, staff users add ``staff``, superusers add
    ``admin``.
    """
    roles = [BASE_ROLE]

    if user.is_staff:
        roles.append(STAFF_ROLE)

    if user.is_superuser:
        roles.append(ADMIN_ROLE)

    return roles
