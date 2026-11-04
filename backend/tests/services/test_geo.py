import math

import pytest

from app.services.geo import bounding_box


def test_box_is_centered_on_point() -> None:
    min_lng, min_lat, max_lng, max_lat = bounding_box(37.5, 127.0, 10)
    assert (min_lng + max_lng) / 2 == pytest.approx(127.0)
    assert (min_lat + max_lat) / 2 == pytest.approx(37.5)


def test_lat_span_matches_radius() -> None:
    _, min_lat, _, max_lat = bounding_box(37.5, 127.0, 10)
    assert (max_lat - min_lat) * 111.32 / 2 == pytest.approx(10)


def test_lng_span_is_corrected_by_cos_lat() -> None:
    min_lng, _, max_lng, _ = bounding_box(37.5, 127.0, 10)
    km_per_deg_lng = 111.32 * math.cos(math.radians(37.5))
    assert (max_lng - min_lng) * km_per_deg_lng / 2 == pytest.approx(10)


def test_box_widens_in_lng_toward_higher_latitude() -> None:
    low = bounding_box(34.0, 127.0, 10)
    high = bounding_box(38.0, 127.0, 10)
    assert (high[2] - high[0]) > (low[2] - low[0])


def test_extreme_latitude_does_not_divide_by_zero() -> None:
    assert bounding_box(90.0, 0.0, 10)[2] > 0
