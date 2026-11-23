"""보안 이벤트 기록. 챗봇 가드·인가·로그인이 모두 여기로 보내고, Grafana는 이 카운터를 본다.

이벤트 종류(event)는 아래 Literal로 고정한다. 대시보드 패널이 이 이름에 의존하므로 바꿀 때는 대시보드도 함께 고친다.
원문 입력·토큰·이메일·좌표는 넘기지 않는다 (사유 코드와 경로만).
"""

import logging
from typing import Literal

from prometheus_client import Counter

SecurityEvent = Literal[
    "unauthorized",  # 401: 토큰 없음·만료·위조, 로그인 실패
    "forbidden",  # 403: 역할·소유권 거부
    "rate_limited",  # 429
    "chat_input_blocked",  # 챗봇 입력 가드 차단
    "chat_output_blocked",  # 챗봇 출력 가드 차단·마스킹
]

_log = logging.getLogger("teamup.security")

SECURITY_EVENTS = Counter(
    "teamup_security_events_total",
    "보안 이벤트 수",
    [
        "event",
        "code",
        "route",
    ],  # route는 /matches/{match_id} 같은 템플릿 (/api/v1 제외, id를 넣지 않는다)
)


def record_security_event(event: SecurityEvent, code: str, route: str = "") -> None:
    SECURITY_EVENTS.labels(event=event, code=code, route=route).inc()
    _log.warning("security_event event=%s code=%s route=%s", event, code, route)


# 챗봇 차단율의 분모. 가드는 요청마다 대화 이력 전체를 다시 검사하므로, 차단율은 요청 수가 아니라 검사 수로 나눈다.
CHAT_REQUESTS = Counter("teamup_chat_requests_total", "챗봇 요청 수 (인증·레이트리밋 통과 후)")
CHAT_GUARD_CHECKS = Counter("teamup_chat_guard_checks_total", "챗봇 가드 검사 수", ["stage"])

GuardStage = Literal["input", "output"]


def count_guard_check(stage: GuardStage) -> None:
    CHAT_GUARD_CHECKS.labels(stage=stage).inc()
