"""좌표 계산 순수 함수 (DB 없이 테스트한다). 좌표는 (lng, lat) 순서가 아니라 인자 이름으로 받는다."""

import math

_KM_PER_DEG_LAT = 111.32  # 위도 1도 ≈ 111.32km (경도는 cos(lat)만큼 줄어든다)
_MAX_ABS_LAT = 89.0  # cos(lat)이 0에 가까워지는 극지방 방지


def bounding_box(lat: float, lng: float, radius_km: float) -> tuple[float, float, float, float]:
    """반경 radius_km를 감싸는 사각형. (min_lng, min_lat, max_lng, max_lat) 순서.

    정밀 거리 필터(ST_Distance_Sphere) 전에 SPATIAL INDEX로 후보를 줄이는 용도라
    원보다 약간 커도 되지만 작으면 안 된다.
    """
    d_lat = radius_km / _KM_PER_DEG_LAT
    safe_lat = max(-_MAX_ABS_LAT, min(_MAX_ABS_LAT, lat))
    d_lng = radius_km / (_KM_PER_DEG_LAT * math.cos(math.radians(safe_lat)))
    return lng - d_lng, lat - d_lat, lng + d_lng, lat + d_lat
