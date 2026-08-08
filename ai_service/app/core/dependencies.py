from fastapi import Header, HTTPException


async def get_current_user_id(x_user_id: str = Header(...)) -> str:
    if not x_user_id:
        print('nop')
        raise HTTPException(status_code=401, detail="Missing user context")
    return int(x_user_id)