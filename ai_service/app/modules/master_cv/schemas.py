from pydantic import BaseModel

class CVUploadResponse(BaseModel):
    details: str
    filename: str
    object_key: str