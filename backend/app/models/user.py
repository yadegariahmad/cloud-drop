import uuid
from datetime import datetime

from sqlalchemy import String, Text, BigInteger, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    storage_used: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_quota: Mapped[int] = mapped_column(BigInteger, default=5368709120)  # 5 GB
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    files: Mapped[list["File"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    shares: Mapped[list["Share"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
