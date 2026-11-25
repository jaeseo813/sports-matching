# 위협 모델

챗봇 가드(파트 A)가 중심이다. 파트 안내는 [README.md](README.md).

## 챗봇 (STRIDE)

| 위협 | 예시 | 막는 곳 | 상태 |
|---|---|---|---|
| 스푸핑 (S) | 다른 사용자인 척 "user_id 3의 일정 알려줘" | 도구는 JWT의 user_id만 사용, 입력 가드 `OTHERS_INFO` | 구현 |
| 스푸핑 (S) | 대화 이력에 가짜 assistant 답을 넣어 맥락 조작 | assistant 이력은 서버 서명(HMAC, 사용자에 묶임)이 맞을 때만 받음, user 이력은 입력 가드 | 구현([003](findings/003-multi-turn-and-forged-history.md)) |
| 변조 (T) | 공지·닉네임에 숨긴 지시문(간접 인젝션) | 도구 결과를 `<data>`로 감싸고 안의 `<`를 이스케이프(구분자 탈출 불가), 시스템 프롬프트 | 구현. 실제 공격에서 LLM이 따르지 않음([002](findings/002-chatbot-live-redteam.md)) |
| 변조 (T) | 여러 턴에 나눠 조금씩 빼내기 | 막힌 턴은 이력에서 빠짐, 시스템 프롬프트 | 재현 안 됨([003](findings/003-multi-turn-and-forged-history.md)) |
| 변조 (T) | 직접 인젝션·탈옥 | 입력 가드(규칙 → LLM 분류) → 시스템 프롬프트 | v2 결합. 세트 내 우회 모두 차단, 분류기 자체도 인젝션 대상 |
| 부인 (R) | 차단된 요청의 기록이 없음 | `record_security_event` (사유 코드만, 원문 없음) | 구현 |
| 정보 노출 (I) | 시스템 프롬프트 추출 | 입력 `PROMPT_EXTRACTION`(규칙 → LLM), 시스템 프롬프트(요약·바꿔 말하기도 거절), 출력 `PROMPT_LEAK`(규칙 → LLM) | 실제 공격 재검증([002](findings/002-chatbot-live-redteam.md), [004](findings/004-output-guard-paraphrase.md)). 예/아니오로 규칙 존재 확인은 받아들임 |
| 정보 노출 (I) | 응답 속 이메일·전화·좌표·주소, 숫자 레이팅 | 출력 가드 마스킹·`RATING_LEAK`·`PERSONAL_INFO`, 도구 스키마에서 PII 제외 | 규칙 → LLM. 실명이라고 밝히지 않은 이름은 못 잡을 수 있음 |
| 정보 노출 (I) | 사용자가 넣은 개인정보가 외부 LLM으로 | 입력 가드 마스킹(이력 포함), LLM 분류기에도 마스킹한 값만 | 규칙. `(at)`·`골뱅이`·한글 숫자 번호까지 마스킹, 그 밖의 변형은 통과 가능 |
| 서비스 거부 (D) | 긴 입력, 반복 호출로 토큰 소모 | 입력 500자, 챗봇 20/5분, 사용자당 24시간 토큰 상한 20만(`CHAT_TOKEN_LIMIT`) | 구현. 인메모리(재시작 시 초기화), 가드 분류 호출 포함 |
| 권한 상승 (E) | "매치 취소해줘"로 쓰기 동작 유도 | 도구 전부 읽기 전용, 출력 `WRITE_CLAIM`(규칙 → LLM) | 구현 |
| 권한 상승 (E) | 응답에 링크·HTML을 넣어 피싱·XSS | 출력 `LINK`·`HTML` 차단, 버튼 주소는 서버가 생성 | 구현 |

평가 결과: [chat-guard-eval.md](chat-guard-eval.md).

## 범위 축소로 받아들인 한계
- 토큰은 access JWT 하나(24시간), 브라우저 저장소에 둔다. XSS가 나면 탈취될 수 있고 서버가 만료 전에 무효화할 수 없다.
- 레이트리밋은 서버 메모리라 재시작하면 초기화된다.
- `GET /metrics`는 `METRICS_TOKEN`(Bearer)으로 보호한다. 토큰을 비우면 `ENV=local`에서만 인증 없이 열린다. 레이트리밋은 없다([README](README.md) B 절).

## 의도적 취약점 (학습용, `main`에 남겨 둠)
- **비밀번호 원문 저장**: `core/security.py`의 `hash_password`/`verify_password`. 교체할 때는 이 두 함수만 바꾼다.
