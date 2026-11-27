from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import NotificationKind, str_enum


class Notification(Base):
    """앱 안 알림. 문구는 저장하지 않고 종류와 매치로 화면에서 만든다."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "read_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    kind: Mapped[NotificationKind] = mapped_column(str_enum(NotificationKind))
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
