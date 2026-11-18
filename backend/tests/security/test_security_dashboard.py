"""보안 대시보드(Grafana JSON)가 코드의 보안 이벤트 이름과 어긋나지 않는지 검사한다.

대시보드에 코드에 없는 event 값(오타 등)이 있으면 패널이 조용히 비어 버리므로 테스트로 막는다.
"""

import json
import re
from functools import cache
from pathlib import Path
from typing import Any, get_args

from app.core.security_events import SecurityEvent

_DASHBOARD = (
    Path(__file__).resolve().parents[3] / "infra/monitoring/grafana/dashboards/security.json"
)
_EVENT_MATCHER = re.compile(r'event\s*(=~|=)\s*"([^"]*)"')


@cache
def _dashboard() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(_DASHBOARD.read_text(encoding="utf-8"))
    return data


def _panels() -> list[dict[str, Any]]:
    panels: list[dict[str, Any]] = []
    for panel in _dashboard().get("panels", []):
        panels.append(panel)
        panels.extend(panel.get("panels", []))  # 접힌 row 안의 패널
    return panels


def _exprs() -> list[str]:
    return [t["expr"] for p in _panels() for t in p.get("targets", []) if t.get("expr")]


def _datasource_uids() -> list[str]:
    uids = []
    for p in _panels():
        for ds in [p.get("datasource"), *(t.get("datasource") for t in p.get("targets", []))]:
            if isinstance(ds, dict):
                uids.append(ds.get("uid", ""))
    return uids


def _event_values(exprs: list[str]) -> set[str]:
    """expr 안의 event 라벨 조건이 가리키는 값. 정규식(=~)은 맞는 Literal 값으로 풀고, 하나도 안 맞으면 원문을 남긴다."""
    known = set(get_args(SecurityEvent))
    used: set[str] = set()
    for expr in exprs:
        for op, value in _EVENT_MATCHER.findall(expr):
            if op == "=":
                used.add(value)
                continue
            matched = {e for e in known if re.fullmatch(value, e)}
            used |= matched or {value}
    return used


def test_dashboard_events_exist_in_code() -> None:
    used = _event_values(_exprs())
    assert used, "대시보드가 이벤트를 하나도 안 쓴다"
    assert used <= set(get_args(SecurityEvent)), (
        f"코드에 없는 event: {used - set(get_args(SecurityEvent))}"
    )


def test_panels_use_increase_or_rate() -> None:
    # 카운터 원값은 uvicorn --reload 때 0으로 돌아가 그래프가 꺾인다. 증가량만 그린다.
    for expr in _exprs():
        if "teamup_security_events_total" in expr:
            assert "increase(" in expr or "rate(" in expr, expr


def test_dashboard_has_scrape_status_panel() -> None:
    assert any('up{job="teamup-api"}' in e for e in _exprs())


def test_dashboard_uses_provisioned_datasource() -> None:
    uids = _datasource_uids()
    assert uids
    assert all(uid == "teamup-prometheus" for uid in uids)


def test_exprs_have_balanced_brackets() -> None:
    # 괄호가 어긋난 PromQL은 Grafana에서 패널 오류로만 보인다. 문법 전체 검사는 Prometheus에서 한다.
    pairs = {")": "(", "]": "[", "}": "{"}
    for expr in _exprs():
        stack: list[str] = []
        for ch in re.sub(r'"[^"]*"', '""', expr):
            if ch in "([{":
                stack.append(ch)
            elif ch in pairs:
                assert stack and stack.pop() == pairs[ch], expr
        assert not stack, expr
