from sqlalchemy import Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import Verdict, str_enum


class PeerReview(TimestampMixin, Base):
    """경기 후 상호 평가. 탈퇴 시 reviewer/reviewee를 NULL로 바꿔 익명화해 보존한다."""

    __tablename__ = "peer_reviews"
    __table_args__ = (
        UniqueConstraint(
            "match_id", "reviewer_id", "reviewee_id", name="uq_peer_reviews_match_pair"
        ),
        # reviewer_id <> reviewee_id (자기 평가 금지)는 서비스에서 검증한다.
        # MariaDB는 ON DELETE SET NULL 컬럼을 CHECK에 쓸 수 없다.
        # "같은 쌍 30일 내 1회만 반영" 조회용
        Index("ix_peer_reviews_pair", "reviewer_id", "reviewee_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verdict: Mapped[Verdict] = mapped_column(str_enum(Verdict))
    manner_flag: Mapped[bool] = mapped_column(Boolean, default=False)  # 매너 불량 신고
