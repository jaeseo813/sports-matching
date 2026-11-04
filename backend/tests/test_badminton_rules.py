from app.sports.badminton import FAQ, RULES


def test_singles_and_doubles_team_sizes() -> None:
    assert RULES.players_per_team == (1, 2)
    assert RULES.team_count == 2


def test_no_positions() -> None:
    assert RULES.positions == ()
    assert RULES.required_per_team == {}


def test_tier_labels_cover_one_to_five() -> None:
    assert sorted(RULES.tier_labels) == [1, 2, 3, 4, 5]
    assert all(label.strip() for label in RULES.tier_labels.values())


def test_faq_entries_are_filled() -> None:
    assert FAQ
    assert all(q.strip() and a.strip() for q, a in FAQ)
