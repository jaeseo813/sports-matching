"""보안 대시보드(Grafana JSON)가 코드의 보안 이벤트 이름과 어긋나지 않는지 검사한다.

대시보드에 코드에 없는 event 값(오타 등)이 있으면 패널이 조용히 비어 버리므로 테스트로 막는다.
"""

import json
import re
from functools import cache
from pathlib import Path
from typing import Any, get_args

from app.core.security_events import SecurityEvent

_MONITORING = Path(__file__).resolve().parents[3] / "infra/monitoring"
_DASHBOARD = _MONITORING / "grafana/dashboards/security.json"
_ALERTS = _MONITORING / "prometheus/alerts.yml"
_EVENT_MATCHER = re.compile(r'event\s*(=~|!~|!=|=)\s*"([^"]*)"')
_GROUP = re.compile(r"\(([^()]*)\)")


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


def _alert_exprs() -> list[str]:
    # PyYAML은 직접 의존성이 아니라서 한 줄짜리 expr만 읽는다(규칙 파일도 한 줄로 쓴다).
    return re.findall(r"^\s*expr:\s*(.+?)\s*$", _ALERTS.read_text(encoding="utf-8"), re.M)


def _expand(pattern: str) -> list[str]:
    """정규식의 (a|b) 묶음과 맨 바깥 | 를 갈래별 패턴으로 펼친다. 갈래 하나의 오타도 잡기 위해서다."""
    group = _GROUP.search(pattern)
    if group:
        head, tail = pattern[: group.start()], pattern[group.end() :]
        return [x for alt in group.group(1).split("|") for x in _expand(head + alt + tail)]
    return pattern.split("|")


def _event_values(exprs: list[str]) -> set[str]:
    """expr 안의 event 라벨 조건이 가리키는 값.

    정규식(=~, !~)은 갈래마다 맞는 Literal 값으로 풀고, 어떤 값과도 안 맞는 갈래는 원문을 남겨 실패하게 한다.
    """
    known = set(get_args(SecurityEvent))
    used: set[str] = set()
    for expr in exprs:
        for op, value in _EVENT_MATCHER.findall(expr):
            if op in ("=", "!="):
                used.add(value)
                continue
            for branch in _expand(value):
                matched = {e for e in known if re.fullmatch(branch, e)}
                used |= matched or {branch}
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
        if re.search(r"teamup_\w+_total", expr):
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


def test_event_matcher_catches_typos() -> None:
    known = set(get_args(SecurityEvent))
    assert not _event_values(['x{event=~"chat_(input|outptu)_blocked"}']) <= known
    assert not _event_values(['x{event!="forbiden"}']) <= known
    assert not _event_values(['x{event!~"forbiden|unauthorized"}']) <= known


def test_alert_rules_use_known_events() -> None:
    exprs = _alert_exprs()
    assert exprs, "alerts.yml에서 expr를 못 찾았다"
    assert _event_values(exprs) <= set(get_args(SecurityEvent))


def test_block_rate_divides_by_guard_checks() -> None:
    # 가드는 요청마다 대화 이력 전체를 다시 검사한다. 요청 수로 나누면 100%를 넘을 수 있다.
    rates = [e for e in _exprs() if "chat_" in e and "/" in e]
    assert rates, "챗봇 차단율 패널이 없다"
    for expr in rates:
        assert "teamup_chat_guard_checks_total" in expr.split("/", 1)[1], expr


def test_block_rate_excludes_outage_and_handles_zero() -> None:
    # 가드 장애(GUARD_UNAVAILABLE)는 공격이 아니다. 차단이 아직 없으면 0%, 검사가 없으면 비운다(NaN 금지).
    rates = [e for e in _exprs() if "chat_" in e and "/" in e]
    for expr in rates:
        if "PII_" in expr and 'code=~"PII_' not in expr:
            assert "GUARD_UNAVAILABLE" in expr, expr
            # 이력 위조(FORGED_HISTORY)는 입력 가드 검사 전에 막혀 분모에 안 들어간다. 분자에 넣으면 100%를 넘는다
            assert "FORGED_HISTORY" in expr, expr
        assert "or vector(0)" in expr, expr
        assert ") > 0" in expr, expr
