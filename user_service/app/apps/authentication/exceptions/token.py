class TokenInvalidError(Exception):
    pass

class TokenExpiredError(Exception):
    pass

class TokenRequestCooldownError(Exception):
    pass