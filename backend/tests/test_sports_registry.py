from app.sports.registry import SPORTS, get_rules


def test_three_sports_registered() -> None:
    assert set(SPORTS) == {"basketball", "football", "badminton"}


def test_rule_id_matches_key() -> None:
    for sport_id in SPORTS:
        assert get_rules(sport_id).id == sport_id
