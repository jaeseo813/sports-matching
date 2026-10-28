from app.models import Base
from app.models.types import GeoPoint

EXPECTED_TABLES = {
    "users",
    "user_locations",
    "user_skills",
    "venues",
    "venue_sports",
    "matches",
    "participations",
    "peer_reviews",
    "team_assignments",
    "matching_weights",
}


def test_all_core_tables_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_geopoint_uses_lng_lat_order() -> None:
    point = GeoPoint()
    to_wkt = point.bind_processor(None)  # type: ignore[arg-type]
    from_wkt = point.result_processor(None, None)  # type: ignore[arg-type]
    assert to_wkt((127.0, 37.5)) == "POINT(127.0 37.5)"  # 경도(lng)가 먼저
    assert from_wkt("POINT(127 37.5)") == (127.0, 37.5)
