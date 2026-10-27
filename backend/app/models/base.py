from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 ORM 모델의 부모. Alembic이 Base.metadata를 읽는다 (모델은 models/ 에서 import)."""
