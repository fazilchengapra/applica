"""Domain errors raised while composing the home aggregate."""


class UserServiceError(Exception):
    """user_service could not be reached or returned an error.

    Distinct from :class:`UserServiceUnavailable` only for readability at the
    call site; both map to a 502/504 at the router.
    """


class UserServiceUnavailable(UserServiceError):
    """user_service did not respond in time or was unreachable."""
