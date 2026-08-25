from fastapi import Header, HTTPException


async def require_admin(
    x_user_is_admin: str | None = Header(default=None),
):
    if x_user_is_admin != "true":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
