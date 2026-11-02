from app.sports.football import FAQ, RULES


def test_futsal_team_sizes() -> None:
    assert RULES.players_per_team == (5, 6)
    assert RULES.team_count == 2


def test_required_positions_are_known() -> None:
    assert set(RULES.required_per_team) <= set(RULES.positions)


def test_tier_labels_cover_one_to_five() -> None:
    assert sorted(RULES.tier_labels) == [1, 2, 3, 4, 5]


def test_faq_entries_are_filled() -> None:
    assert FAQ
    assert all(q.strip() and a.strip() for q, a in FAQ)
