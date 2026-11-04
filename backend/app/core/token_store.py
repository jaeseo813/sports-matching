"""refresh 토큰 회전·재사용 감지용 저장소.

지금은 프로세스 메모리에만 둔다 (Redis 없으면 인메모리 degrade 규칙). 서버를 재시작하거나
워커가 여러 개면 로그인이 풀리거나 재사용 감지가 어긋난다 — Redis 구현으로 교체할 자리.
"""

from typing import Literal

ConsumeResult = Literal["ok", "reused", "unknown"]


class TokenStore:
    def __init__(self) -> None:
        self._active: dict[str, str] = {}  # jti -> family
        self._used: dict[str, str] = {}  # 이미 회전된 jti -> family
        self._revoked: set[str] = set()  # 폐기된 family

    def issue(self, jti: str, family: str) -> None:
        self._active[jti] = family

    def consume(self, jti: str, family: str) -> ConsumeResult:
        """refresh 토큰 1회 사용. 이미 쓴 토큰이 다시 오면 같은 family 전체를 폐기한다."""
        if family in self._revoked:
            return "unknown"
        if jti in self._used:
            self.revoke_family(family)
            return "reused"
        if self._active.pop(jti, None) is None:
            return "unknown"
        self._used[jti] = family
        return "ok"

    def revoke_family(self, family: str) -> None:
        self._revoked.add(family)
        self._active = {j: f for j, f in self._active.items() if f != family}


token_store = TokenStore()
