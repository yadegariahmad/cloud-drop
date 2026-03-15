import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.aws import delete_s3_object
from app.models.file import File
from app.models.user import User


class FileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pending(
        self,
        owner_id: uuid.UUID,
        filename: str,
        s3_key: str,
        mime_type: str,
        size_bytes: int,
    ) -> File:
        file = File(
            owner_id=owner_id,
            filename=filename,
            s3_key=s3_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            status="pending",
        )
        self.db.add(file)
        await self.db.commit()
        await self.db.refresh(file)
        return file

    async def confirm(self, file_id: uuid.UUID, owner_id: uuid.UUID) -> File:
        file = await self._get_owned_file(file_id, owner_id)

        if file.status != "pending":
            raise HTTPException(status_code=400, detail="File is not in pending status")

        file.status = "active"

        user = await self.db.get(User, owner_id)
        if user:
            user.storage_used += file.size_bytes

        await self.db.commit()
        await self.db.refresh(file)
        return file

    async def list_files(
        self, owner_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[File], int]:
        count_query = select(func.count()).select_from(File).where(
            File.owner_id == owner_id, File.status == "active"
        )
        total = (await self.db.execute(count_query)).scalar() or 0

        query = (
            select(File)
            .where(File.owner_id == owner_id, File.status == "active")
            .order_by(File.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        files = list(result.scalars().all())

        return files, total

    async def get_file(self, file_id: uuid.UUID, owner_id: uuid.UUID) -> File:
        return await self._get_owned_file(file_id, owner_id)

    async def delete_file(self, file_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        file = await self._get_owned_file(file_id, owner_id)

        if file.status == "deleted":
            raise HTTPException(status_code=404, detail="File not found")

        file.status = "deleted"

        user = await self.db.get(User, owner_id)
        if user and file.status != "pending":
            user.storage_used = max(0, user.storage_used - file.size_bytes)

        try:
            delete_s3_object(file.s3_key)
        except Exception:
            pass  # S3 deletion is best-effort

        await self.db.commit()

    async def _get_owned_file(self, file_id: uuid.UUID, owner_id: uuid.UUID) -> File:
        file = await self.db.get(File, file_id)
        if not file or file.owner_id != owner_id:
            raise HTTPException(status_code=404, detail="File not found")
        return file
