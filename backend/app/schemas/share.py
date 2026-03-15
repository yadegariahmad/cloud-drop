import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ShareCreate(BaseModel):
    file_id: uuid.UUID
    ttl: str = "24h"


class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_id: uuid.UUID
    owner_id: uuid.UUID
    expires_at: datetime
    is_revoked: bool
    access_count: int
    created_at: datetime
    signed_url: str | None = None


class SharePublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime_type: str | None
    size_bytes: int
    signed_url: str


class ShareListResponse(BaseModel):
    shares: list[ShareOut]
    total: int
