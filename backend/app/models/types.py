from typing import Any

from sqlalchemy import func
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import UserDefinedType


class GeoPoint(UserDefinedType[tuple[float, float]]):
    """MariaDB POINT. 파이썬에서는 (lng, lat) 튜플로 다룬다.

    SRID 4326은 DB가 강제하지 않는다(MariaDB의 REF_SYSTEM_ID는 효력이 없음을 확인).
    ORM으로 저장하면 항상 ST_GeomFromText(..., 4326)으로 들어가고, raw SQL도 반드시 4326을 쓴다.

    주의: WKT는 POINT(lng lat) 순서다 (경도 먼저). 위도·경도 순서를 뒤집지 말 것.
    SPATIAL INDEX를 걸려면 컬럼이 NOT NULL이어야 한다.
    바운딩 박스/거리 쿼리 같은 공간 raw SQL은 repositories/ 에만 둔다.
    """

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return "POINT"

    def bind_processor(self, dialect: Dialect) -> Any:
        def process(value: tuple[float, float] | None) -> str | None:
            if value is None:
                return None
            lng, lat = value
            return f"POINT({lng} {lat})"

        return process

    def bind_expression(self, bindvalue: Any) -> ColumnElement[Any]:
        return func.ST_GeomFromText(bindvalue, 4326)

    def column_expression(self, col: Any) -> ColumnElement[Any]:
        return func.ST_AsText(col, type_=self)

    def result_processor(self, dialect: Dialect, coltype: Any) -> Any:
        def process(value: str | None) -> tuple[float, float] | None:
            if value is None:
                return None
            lng, lat = value.removeprefix("POINT(").removesuffix(")").split()
            return float(lng), float(lat)

        return process
