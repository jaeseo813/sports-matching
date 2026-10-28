# Alembic이 모든 테이블을 알도록 여기서 전부 import 한다
from app.models.base import Base
from app.models.match import Match, Participation, TeamAssignment
from app.models.matching_weight import MatchingWeight
from app.models.review import PeerReview
from app.models.user import User, UserLocation, UserSkill
from app.models.venue import Venue, VenueSport

__all__ = [
    "Base",
    "Match",
    "MatchingWeight",
    "Participation",
    "PeerReview",
    "TeamAssignment",
    "User",
    "UserLocation",
    "UserSkill",
    "Venue",
    "VenueSport",
]
