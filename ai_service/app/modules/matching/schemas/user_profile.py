from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: int | None
    target_role: str | None
    cv_embedding: list[float] | None
    skills: set[str]
