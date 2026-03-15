import uuid
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.aws import generate_cloudfront_signed_url
from app.models.user import User
from app.schemas.share import ShareCreate, ShareOut, SharePublicOut, ShareListResponse
from app.services.share_service import ShareService

router = APIRouter(prefix="/shares", tags=["shares"])
public_router = APIRouter(prefix="/public/shares", tags=["public"])

TTL_OPTIONS = {"1h": 3600, "24h": 86400, "7d": 604800}


@router.post("", response_model=ShareOut, status_code=201)
async def create_share(
    body: ShareCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ttl_seconds = TTL_OPTIONS.get(body.ttl, 86400)
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

    share = await ShareService(db).create(
        file_id=body.file_id,
        owner_id=current_user.id,
        expires_at=expires_at,
    )

    signed_url = generate_cloudfront_signed_url(share.file.s3_key, expires_at)
    share_out = ShareOut.model_validate(share)
    share_out.signed_url = signed_url
    return share_out


@router.get("", response_model=ShareListResponse)
async def list_shares(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shares, total = await ShareService(db).list_shares(current_user.id, skip, limit)
    return ShareListResponse(shares=shares, total=total)


@router.delete("/{share_id}", status_code=204)
async def revoke_share(
    share_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ShareService(db).revoke(share_id, owner_id=current_user.id)


@router.get("/{share_id}/url")
async def get_share_url(
    share_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ShareService(db)
    share = await service.get_public_share(share_id)
    if share.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Share not found")

    signed_url = generate_cloudfront_signed_url(share.file.s3_key, share.expires_at)
    return {"signed_url": signed_url}


@public_router.get("/{share_id}", response_model=SharePublicOut)
async def get_public_share(
    share_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = ShareService(db)
    share = await service.get_public_share(share_id)

    signed_url = generate_cloudfront_signed_url(share.file.s3_key, share.expires_at)
    return SharePublicOut(
        id=share.id,
        filename=share.file.filename,
        mime_type=share.file.mime_type,
        size_bytes=share.file.size_bytes,
        signed_url=signed_url,
    )
