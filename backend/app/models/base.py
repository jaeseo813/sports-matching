from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """모든 ORM 모델의 부모. Alembic이 Base.metadata를 읽는다 (모델은 models/ 에서 import)."""


class TimestampMixin:
    # 시각은 UTC로 저장한다 (DB 서버 타임존 = UTC)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
