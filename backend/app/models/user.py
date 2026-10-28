from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import Gender, Role, str_enum
from app.models.types import GeoPoint


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(30), unique=True)
    gender: Mapped[Gender] = mapped_column(str_enum(Gender))
    birth_year: Mapped[int] = mapped_column(SmallInteger)  # 미성년자 가입 제외 판단용
    role: Mapped[Role] = mapped_column(str_enum(Role), default=Role.USER)
    # 매너 점수(0~5). 기본 3.0 → S_host 0.6 (경기 3회 미만의 기본값과 같다)
    manner_score: Mapped[float] = mapped_column(Float, default=3.0)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    no_show_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)  # 탈퇴 시각


class UserLocation(TimestampMixin, Base):
    """활동 기준점. 사용자당 최대 2개 (slot 1, 2)."""

    __tablename__ = "user_locations"
    __table_args__ = (
        UniqueConstraint("user_id", "slot", name="uq_user_locations_user_slot"),
        CheckConstraint("slot IN (1, 2)", name="ck_user_locations_slot"),
        CheckConstraint("max_distance_km BETWEEN 1 AND 50", name="ck_user_locations_dist"),
        Index("ix_user_locations_point", "point", mysql_prefix="SPATIAL"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    slot: Mapped[int] = mapped_column(SmallInteger)
    label: Mapped[str] = mapped_column(String(50))
    point: Mapped[tuple[float, float]] = mapped_column(GeoPoint)  # (lng, lat)
    max_distance_km: Mapped[int] = mapped_column(SmallInteger, default=10)  # S_dist의 d_max


class UserSkill(TimestampMixin, Base):
    """종목별 실력. rating/RD는 서버 내부 값이며 사용자에게 숫자로 노출하지 않는다."""

    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "sport", name="uq_user_skills_user_sport"),
        CheckConstraint("self_tier BETWEEN 1 AND 5", name="ck_user_skills_tier"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    sport: Mapped[str] = mapped_column(String(20))
    self_tier: Mapped[int] = mapped_column(SmallInteger)  # 자기평가 1~5
    years_played: Mapped[int] = mapped_column(SmallInteger, default=0)
    rating: Mapped[float] = mapped_column(Float)
    rd: Mapped[float] = mapped_column(Float)  # Glicko-2 rating deviation
    volatility: Mapped[float] = mapped_column(Float, default=0.06)
    trend: Mapped[int] = mapped_column(SmallInteger, default=0)  # -1 ↓ / 0 → / 1 ↑
    games_rated: Mapped[int] = mapped_column(Integer, default=0)
    positions: Mapped[list[str] | None] = mapped_column(JSON)  # 선호 포지션 (종목별 값)
