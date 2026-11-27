"""보안 경보 → 디스코드 전송 설정 검사 (파트 B).

웹훅 주소는 비밀값이다(아는 사람은 누구나 채널에 글을 쓸 수 있다). 레포에 들어가지 않는지,
Prometheus → Alertmanager → 디스코드 연결이 끊기지 않는지 확인한다.
PyYAML은 직접 의존성이 아니라서 텍스트로 검사한다.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MONITORING = _ROOT / "infra/monitoring"
_ALERTS = _MONITORING / "prometheus/alerts.yml"
_AM = _MONITORING / "alertmanager/alertmanager.yml"
_AM_OFF = _MONITORING / "alertmanager/alertmanager-off.yml"
_COMPOSE = _ROOT / "docker-compose.yml"
_WEBHOOK = re.compile(r"discord(app)?\.com/api/webhooks/", re.I)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _rules() -> list[str]:
    """alerts.yml의 규칙을 `- alert:` 단위로 자른다."""
    return re.split(r"^\s*- alert:", _read(_ALERTS), flags=re.M)[1:]


def test_webhook_url_is_not_committed() -> None:
    files = [*_MONITORING.rglob("*"), _COMPOSE, _ROOT / ".env.example"]
    leaked = [str(f) for f in files if f.is_file() and _WEBHOOK.search(_read(f))]
    assert not leaked, f"디스코드 웹훅 주소가 레포에 있다: {leaked}"


def test_alertmanager_reads_webhook_from_file() -> None:
    config = _read(_AM)
    assert "discord_configs:" in config
    assert "webhook_url_file: /alertmanager/discord_webhook" in config
    assert not re.search(r"^\s*webhook_url:", config, re.M), "주소를 설정에 직접 쓰지 않는다"
    assert "send_resolved: true" in config


def test_compose_passes_webhook_from_env_and_falls_back() -> None:
    compose = _read(_COMPOSE)
    assert "DISCORD_WEBHOOK_URL: ${DISCORD_WEBHOOK_URL:-}" in compose
    assert "> /alertmanager/discord_webhook" in compose
    assert "alertmanager-off.yml" in compose and _AM_OFF.is_file()
    assert '"127.0.0.1:9093:9093"' in compose, "Alertmanager는 내 컴퓨터에서만 연다"


def test_off_config_sends_nowhere() -> None:
    config = _read(_AM_OFF)
    assert "receiver: none" in config
    assert "_configs:" not in config


def test_prometheus_sends_alerts_to_alertmanager() -> None:
    prometheus = _read(_MONITORING / "prometheus/prometheus.yml")
    assert re.search(r"^alerting:.*\n\s*alertmanagers:", prometheus, re.M)
    assert '"alertmanager:9093"' in prometheus
    assert re.search(r"^  alertmanager:\s*$", _read(_COMPOSE), re.M), "compose 서비스 이름과 맞춘다"


def test_every_rule_has_message_text() -> None:
    rules = _rules()
    assert len(rules) >= 3
    for rule in rules:
        name = rule.split()[0]
        assert re.search(r"^\s*summary:", rule, re.M), f"{name}: 메시지 첫 줄(summary)이 없다"
        assert re.search(r"^\s*description:.*\$value", rule, re.M), f"{name}: 지금 값이 없다"


def test_rules_count_exactly() -> None:
    # increase()는 구간 끝을 추정으로 늘려 403 12번을 "18회"로 보낸다. 메시지에 숫자가 나가므로 쓰지 않는다.
    for rule in _rules():
        expr = re.search(r"^\s*expr:\s*(.+)$", rule, re.M)
        assert expr, rule
        assert "increase(" not in expr.group(1), expr.group(1)
        assert "max_over_time(" in expr.group(1) and "min_over_time(" in expr.group(1)


def test_chat_alert_uses_same_exclusions_as_block_rate() -> None:
    chat = next(r for r in _rules() if r.split()[0] == "ChatGuardBlockBurst")
    for code in ("PII_.*", "GUARD_UNAVAILABLE", "FORGED_HISTORY"):
        assert code in chat, f"차단율 패널처럼 {code}는 빼야 한다"
