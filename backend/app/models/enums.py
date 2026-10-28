from enum import StrEnum

from sqlalchemy import Enum


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


class GenderPolicy(StrEnum):
    ANY = "any"
    MALE_ONLY = "male_only"
    FEMALE_ONLY = "female_only"


class MatchStatus(StrEnum):
    OPEN = "open"
    FULL = "full"
    CONFIRMED = "confirmed"
    PLAYING = "playing"
    COMPLETED = "completed"
    CANCELED = "canceled"


class ParticipationStatus(StrEnum):
    APPLIED = "applied"  # 신청함 (주최자 승인 대기)
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELED = "canceled"  # 본인이 취소
    ATTENDED = "attended"
    NO_SHOW = "no_show"


class Verdict(StrEnum):
    """상호 평가: 상대가 나보다 어떤가."""

    BETTER = "better"
    SIMILAR = "similar"
    WORSE = "worse"


def str_enum(cls: type[StrEnum]) -> Enum:
    """네이티브 ENUM 대신 VARCHAR로 저장 (값 추가 시 마이그레이션이 쉽다)."""
    return Enum(cls, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])
