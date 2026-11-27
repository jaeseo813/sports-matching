"""원문으로 저장된 비밀번호를 Argon2 해시로 바꾼다 (#39에서 해싱으로 바꾸기 전에 가입한 계정)

Revision ID: c3d4e5f6a7b8
Revises: b7c1e2f3a4d5
Create Date: 2026-11-27 11:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from argon2 import PasswordHasher

revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b7c1e2f3a4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 해시는 "$argon2"로 시작한다. 그 밖의 값은 원문이므로 해시해서 덮어쓴다 (다시 실행해도 해시는 건드리지 않는다)
    conn = op.get_bind()
    hasher = PasswordHasher()
    rows = conn.execute(
        sa.text("SELECT id, password FROM users WHERE password NOT LIKE '$argon2%'")
    )
    for user_id, plain in rows.all():
        conn.execute(
            sa.text("UPDATE users SET password = :hashed WHERE id = :id"),
            {"hashed": hasher.hash(plain), "id": user_id},
        )


def downgrade() -> None:
    pass  # 해시에서 원문을 되돌릴 수 없고, 되돌려서도 안 된다
