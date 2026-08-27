from pydantic import BaseModel


class NotificationEvent(BaseModel):
    event_type: str
    user_id: str
    payload: dict
