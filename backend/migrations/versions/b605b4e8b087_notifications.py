"""앱 안 알림(매칭 수락·확정) 테이블

Revision ID: b605b4e8b087
Revises: b7c1e2f3a4d5
Create Date: 2026-11-25 17:47:30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b605b4e8b087"
down_revision: str | Sequence[str] | None = "b7c1e2f3a4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])


def downgrade() -> None:
    op.drop_table(
        "notifications"
    )  # 인덱스도 함께 지워진다 (외래 키가 쓰는 인덱스라 먼저 지울 수 없다)
