import uuid
from datetime import datetime, UTC

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.file import File
from app.models.share import Share


class ShareService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        file_id: uuid.UUID,
        owner_id: uuid.UUID,
        expires_at: datetime,
    ) -> Share:
        # Validate file ownership and active status
        file = await self.db.get(File, file_id)
        if not file or file.owner_id != owner_id:
            raise HTTPException(status_code=404, detail="File not found")
        if file.status != "active":
            raise HTTPException(status_code=400, detail="File is not active")

        share = Share(
            file_id=file_id,
            owner_id=owner_id,
            expires_at=expires_at,
        )
        self.db.add(share)
        await self.db.commit()

        # Eager-load file relationship
        result = await self.db.execute(
            select(Share)
            .where(Share.id == share.id)
            .options(selectinload(Share.file))
        )
        return result.scalar_one()

    async def list_shares(
        self, owner_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[Share], int]:
        count_query = select(func.count()).select_from(Share).where(
            Share.owner_id == owner_id
        )
        total = (await self.db.execute(count_query)).scalar() or 0

        query = (
            select(Share)
            .where(Share.owner_id == owner_id)
            .options(selectinload(Share.file))
            .order_by(Share.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        shares = list(result.scalars().all())

        return shares, total

    async def revoke(self, share_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        share = await self.db.get(Share, share_id)
        if not share or share.owner_id != owner_id:
            raise HTTPException(status_code=404, detail="Share not found")

        share.is_revoked = True
        await self.db.commit()

    async def get_public_share(self, share_id: uuid.UUID) -> Share:
        result = await self.db.execute(
            select(Share)
            .where(Share.id == share_id)
            .options(selectinload(Share.file))
        )
        share = result.scalar_one_or_none()

        if not share:
            raise HTTPException(status_code=404, detail="Share not found")
        if share.is_revoked:
            raise HTTPException(status_code=410, detail="Share has been revoked")
        expires = share.expires_at.replace(tzinfo=UTC) if share.expires_at.tzinfo is None else share.expires_at
        if expires < datetime.now(UTC):
            raise HTTPException(status_code=410, detail="Share has expired")

        # Increment access count
        share.access_count += 1
        share.last_accessed = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(share)

        return share
