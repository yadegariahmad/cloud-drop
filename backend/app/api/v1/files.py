import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.aws import generate_presigned_upload_url
from app.models.user import User
from app.schemas.file import UploadUrlRequest, UploadUrlResponse, FileOut, FileListResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload-url", response_model=UploadUrlResponse)
async def request_upload_url(
    body: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.storage_used + body.size_bytes > current_user.storage_quota:
        raise HTTPException(status_code=400, detail="Storage quota exceeded")

    s3_key = f"users/{current_user.id}/{uuid.uuid4()}/{body.filename}"
    upload_url = generate_presigned_upload_url(s3_key, body.mime_type)

    file = await FileService(db).create_pending(
        owner_id=current_user.id,
        filename=body.filename,
        s3_key=s3_key,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
    )
    return UploadUrlResponse(upload_url=upload_url, file_id=file.id, s3_key=s3_key)


@router.patch("/{file_id}/confirm", response_model=FileOut)
async def confirm_upload(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FileService(db).confirm(file_id, owner_id=current_user.id)


@router.get("", response_model=FileListResponse)
async def list_files(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    files, total = await FileService(db).list_files(current_user.id, skip, limit)
    return FileListResponse(files=files, total=total)


@router.get("/{file_id}", response_model=FileOut)
async def get_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FileService(db).get_file(file_id, current_user.id)


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FileService(db).delete_file(file_id, current_user.id)
