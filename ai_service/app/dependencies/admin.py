from fastapi import Header, HTTPException


async def require_admin(
    x_admin_authorized: str | None = Header(default=None),
):
    if x_admin_authorized != "true":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
