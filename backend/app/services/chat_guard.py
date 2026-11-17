"""챗봇 입력·출력 가드 (AGENTS.md 5절). 챗봇은 LLM 호출 앞뒤에서 이 두 함수만 부른다.

판정 방식(규칙·마스킹 / LLM 분류 / 결합)은 미정이다. 어느 쪽이든 아래 두 함수의 형태는 유지하고 안쪽만 바꾼다.
LLM 판정이 들어갈 수 있어 async로 둔다. 차단·마스킹하면 record_security_event로 남긴다.
"""

from dataclasses import dataclass

from app.core.security_events import record_security_event

MAX_INPUT_CHARS = 500


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    text: str  # 다음 단계로 넘길 텍스트 (마스킹했으면 마스킹된 값)
    code: str | None = None  # 차단·마스킹 사유 코드 (예: TOO_LONG, PROMPT_INJECTION, PII)


async def check_input(text: str) -> GuardResult:
    if len(text) > MAX_INPUT_CHARS:
        record_security_event("chat_input_blocked", "TOO_LONG")
        return GuardResult(allowed=False, text="", code="TOO_LONG")
    # TODO(가드 담당): 인젝션·탈옥, 타인 정보 요청, 범위 밖 요청, 입력 속 개인정보
    return GuardResult(allowed=True, text=text)


async def check_output(text: str) -> GuardResult:
    # TODO(가드 담당): 개인정보, 시스템 프롬프트 노출, 허용 안 된 HTML·링크, 쓰기 동작 안내
    return GuardResult(allowed=True, text=text)
