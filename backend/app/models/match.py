from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import GenderPolicy, MatchStatus, ParticipationStatus, str_enum


class Match(TimestampMixin, Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("tier_min BETWEEN 1 AND 5", name="ck_matches_tier_min"),
        CheckConstraint("tier_max BETWEEN 1 AND 5", name="ck_matches_tier_max"),
        CheckConstraint("tier_min <= tier_max", name="ck_matches_tier_order"),
        CheckConstraint("min_players >= 2 AND min_players <= capacity", name="ck_matches_players"),
        Index("ix_matches_feed", "sport", "status", "starts_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sport: Mapped[str] = mapped_column(String(20))
    host_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(1000))
    starts_at: Mapped[datetime] = mapped_column(DateTime)  # UTC
    duration_min: Mapped[int] = mapped_column(SmallInteger)
    team_size: Mapped[int] = mapped_column(SmallInteger)  # 팀당 인원 (종목 규칙으로 검증)
    capacity: Mapped[int] = mapped_column(SmallInteger)  # 총 정원
    min_players: Mapped[int] = mapped_column(SmallInteger)  # 이 인원 이상이면 확정 가능
    gender_policy: Mapped[GenderPolicy] = mapped_column(
        str_enum(GenderPolicy), default=GenderPolicy.ANY
    )
    tier_min: Mapped[int] = mapped_column(SmallInteger, default=1)
    tier_max: Mapped[int] = mapped_column(SmallInteger, default=5)
    status: Mapped[MatchStatus] = mapped_column(str_enum(MatchStatus), default=MatchStatus.OPEN)


class Participation(TimestampMixin, Base):
    """매치 신청. (match_id, user_id) 유니크로 중복 신청을 막는다."""

    __tablename__ = "participations"
    __table_args__ = (
        UniqueConstraint("match_id", "user_id", name="uq_participations_match_user"),
        Index("ix_participations_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[ParticipationStatus] = mapped_column(
        str_enum(ParticipationStatus), default=ParticipationStatus.APPLIED
    )
    position: Mapped[str | None] = mapped_column(String(20))  # 희망/배정 포지션


class TeamAssignment(Base):
    """팀 분배 결과. 밸런서가 만들고 주최자가 수동 조정할 수 있다."""

    __tablename__ = "team_assignments"
    __table_args__ = (
        UniqueConstraint("match_id", "user_id", name="uq_team_assignments_match_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    team_no: Mapped[int] = mapped_column(SmallInteger)
    position: Mapped[str | None] = mapped_column(String(20))
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
