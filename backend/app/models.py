"""ORM alinhado ao schema Prisma (tabelas com nomes PascalCase)."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, false, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    """Prisma @updatedAt / @default(now) nem sempre cria DEFAULT no Postgres; preenche no INSERT."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Store(Base):
    __tablename__ = "Store"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), default=_utc_now, server_default=func.now()
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, server_default=func.now()
    )
    externalStoreId: Mapped[str] = mapped_column("externalStoreId", Text, unique=True)
    timeZone: Mapped[str] = mapped_column("timeZone", Text, server_default="America/Sao_Paulo")
    displayName: Mapped[Optional[str]] = mapped_column("displayName", Text, nullable=True)
    encryptedRefresh: Mapped[Optional[str]] = mapped_column("encryptedRefresh", Text, nullable=True)
    accessToken: Mapped[Optional[str]] = mapped_column("accessToken", Text, nullable=True)
    accessExpiresAt: Mapped[Optional[datetime]] = mapped_column(
        "accessExpiresAt", DateTime(timezone=True), nullable=True
    )

    settings_rel: Mapped[Optional["StoreSettings"]] = relationship(back_populates="store_rel")
    job_state_rel: Mapped[Optional["JobState"]] = relationship(back_populates="store_rel")
    price_baseline_rel: Mapped[Optional["PriceBaseline"]] = relationship(back_populates="store_rel")


class StoreSettings(Base):
    __tablename__ = "StoreSettings"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    storeId: Mapped[str] = mapped_column("storeId", Text, ForeignKey("Store.id", ondelete="CASCADE"), unique=True)
    discountPercent: Mapped[int] = mapped_column("discountPercent", Integer, server_default="15")
    leadMinutes: Mapped[int] = mapped_column("leadMinutes", Integer, server_default="60")
    activeWeekdays: Mapped[int] = mapped_column("activeWeekdays", Integer, server_default="62")
    routineEnabled: Mapped[bool] = mapped_column("routineEnabled", Boolean, server_default=false())
    promoCategoryIds: Mapped[list[int]] = mapped_column(
        "promoCategoryIds", ARRAY(Integer), nullable=False, server_default=text("'{}'::integer[]")
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, server_default=func.now()
    )

    store_rel: Mapped["Store"] = relationship(back_populates="settings_rel")


class JobState(Base):
    __tablename__ = "JobState"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    storeId: Mapped[str] = mapped_column("storeId", Text, ForeignKey("Store.id", ondelete="CASCADE"), unique=True)
    lastRunAt: Mapped[Optional[datetime]] = mapped_column("lastRunAt", DateTime(timezone=True), nullable=True)
    lastError: Mapped[Optional[str]] = mapped_column("lastError", Text, nullable=True)
    promoAppliedForDate: Mapped[Optional[str]] = mapped_column("promoAppliedForDate", Text, nullable=True)
    lastRevertDate: Mapped[Optional[str]] = mapped_column("lastRevertDate", Text, nullable=True)

    store_rel: Mapped["Store"] = relationship(back_populates="job_state_rel")


class PriceBaseline(Base):
    __tablename__ = "PriceBaseline"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    storeId: Mapped[str] = mapped_column("storeId", Text, ForeignKey("Store.id", ondelete="CASCADE"), unique=True)
    payload: Mapped[str] = mapped_column("payload", Text)
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, server_default=func.now()
    )

    store_rel: Mapped["Store"] = relationship(back_populates="price_baseline_rel")


class Session(Base):
    __tablename__ = "Session"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    storeId: Mapped[str] = mapped_column("storeId", Text, ForeignKey("Store.id", ondelete="CASCADE"))
    expiresAt: Mapped[datetime] = mapped_column("expiresAt", DateTime(timezone=True))
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), default=_utc_now, server_default=func.now()
    )
