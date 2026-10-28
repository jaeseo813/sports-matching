from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.types import GeoPoint


class Venue(TimestampMixin, Base):
    """구장. 관리자가 등록하는 마스터 데이터."""

    __tablename__ = "venues"
    __table_args__ = (Index("ix_venues_point", "point", mysql_prefix="SPATIAL"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    point: Mapped[tuple[float, float]] = mapped_column(GeoPoint)  # (lng, lat)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class VenueSport(Base):
    """구장이 지원하는 종목 (체육관 하나가 여러 종목을 지원할 수 있다)."""

    __tablename__ = "venue_sports"

    venue_id: Mapped[int] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"), primary_key=True
    )
    sport: Mapped[str] = mapped_column(String(20), primary_key=True)
