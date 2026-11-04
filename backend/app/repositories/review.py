from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ParticipationStatus, Verdict
from app.models.match import Match, Participation
from app.models.review import PeerReview
from app.models.user import User, UserSkill


class DuplicateReviewError(Exception):
    """같은 경기에서 같은 상대를 이미 평가했다 (uq_peer_reviews_match_pair)."""


class ReviewRepository(Protocol):
    async def participant_statuses(self, match_id: int) -> dict[int, ParticipationStatus]: ...
    async def add_review(
        self,
        *,
        match_id: int,
        reviewer_id: int,
        reviewee_id: int,
        verdict: Verdict,
        manner_flag: bool,
    ) -> PeerReview: ...
    async def list_reviews(self, match_id: int) -> list[PeerReview]: ...
    async def recent_pairs(
        self, user_ids: set[int], since: datetime, exclude_match_id: int
    ) -> frozenset[tuple[int, int]]: ...
    async def skills(self, user_ids: set[int], sport: str) -> dict[int, UserSkill]: ...
    async def users(self, user_ids: set[int]) -> dict[int, User]: ...
    async def commit(self) -> None: ...


class SqlReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def participant_statuses(self, match_id: int) -> dict[int, ParticipationStatus]:
        stmt = select(Participation.user_id, Participation.status).where(
            Participation.match_id == match_id
        )
        return {uid: status for uid, status in (await self._session.execute(stmt)).all()}

    async def add_review(
        self,
        *,
        match_id: int,
        reviewer_id: int,
        reviewee_id: int,
        verdict: Verdict,
        manner_flag: bool,
    ) -> PeerReview:
        review = PeerReview(
            match_id=match_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            verdict=verdict,
            manner_flag=manner_flag,
        )
        self._session.add(review)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateReviewError from exc
        return review

    async def list_reviews(self, match_id: int) -> list[PeerReview]:
        stmt = select(PeerReview).where(PeerReview.match_id == match_id).order_by(PeerReview.id)
        return list((await self._session.execute(stmt)).scalars())

    async def recent_pairs(
        self, user_ids: set[int], since: datetime, exclude_match_id: int
    ) -> frozenset[tuple[int, int]]:
        """since 이후 레이팅에 반영된 다른 경기에서 이미 평가한 (평가자, 대상) 쌍."""
        if not user_ids:
            return frozenset()
        stmt = (
            select(PeerReview.reviewer_id, PeerReview.reviewee_id)
            .join(Match, Match.id == PeerReview.match_id)
            .where(
                Match.rated_at.is_not(None),
                Match.rated_at >= since,
                PeerReview.match_id != exclude_match_id,
                PeerReview.reviewer_id.in_(user_ids),
                PeerReview.reviewee_id.in_(user_ids),
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return frozenset((a, b) for a, b in rows if a is not None and b is not None)

    async def skills(self, user_ids: set[int], sport: str) -> dict[int, UserSkill]:
        if not user_ids:
            return {}
        stmt = select(UserSkill).where(UserSkill.user_id.in_(user_ids), UserSkill.sport == sport)
        return {s.user_id: s for s in (await self._session.execute(stmt)).scalars()}

    async def users(self, user_ids: set[int]) -> dict[int, User]:
        if not user_ids:
            return {}
        stmt = select(User).where(User.id.in_(user_ids))
        return {u.id: u for u in (await self._session.execute(stmt)).scalars()}

    async def commit(self) -> None:
        await self._session.commit()
