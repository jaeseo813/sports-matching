"""경기 중(playing) 상태 제거: 남아 있는 매치는 종료(completed)로 바꾼다

Revision ID: b7c1e2f3a4d5
Revises: da424946b40b
Create Date: 2026-11-17 17:00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b7c1e2f3a4d5"
down_revision: str | Sequence[str] | None = "da424946b40b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # status는 VARCHAR라 스키마 변경은 없다. 모델에 없는 값이 남으면 읽을 때 오류가 나므로 데이터만 옮긴다
    op.execute("UPDATE matches SET status = 'completed' WHERE status = 'playing'")


def downgrade() -> None:
    pass  # 어느 매치가 playing이었는지 알 수 없어 되돌리지 않는다
