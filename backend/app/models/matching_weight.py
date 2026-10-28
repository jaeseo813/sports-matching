from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MatchingWeight(Base):
    """추천 스코어링 가중치. 코드가 아니라 DB에 둔다 (is_active인 행 1개를 사용)."""

    __tablename__ = "matching_weights"
    __table_args__ = (
        CheckConstraint(
            "w_dist BETWEEN 0 AND 1 AND w_skill BETWEEN 0 AND 1 AND w_time BETWEEN 0 AND 1 "
            "AND w_host BETWEEN 0 AND 1 AND w_fill BETWEEN 0 AND 1",
            name="ck_matching_weights_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    w_dist: Mapped[float] = mapped_column(Float)
    w_skill: Mapped[float] = mapped_column(Float)
    w_time: Mapped[float] = mapped_column(Float)
    w_host: Mapped[float] = mapped_column(Float)
    w_fill: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
