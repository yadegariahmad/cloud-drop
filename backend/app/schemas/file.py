import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UploadUrlRequest(BaseModel):
    filename: str
    size_bytes: int
    mime_type: str


class UploadUrlResponse(BaseModel):
    upload_url: str
    file_id: uuid.UUID
    s3_key: str


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    filename: str
    s3_key: str
    mime_type: str | None
    size_bytes: int
    status: str
    created_at: datetime
    updated_at: datetime


class FileListResponse(BaseModel):
    files: list[FileOut]
    total: int
