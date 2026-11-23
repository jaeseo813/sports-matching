# 챗봇 가드 공격 세트

한 줄에 문장 하나. `#`으로 시작하는 줄과 빈 줄은 무시한다. 모두 더미 데이터(가짜 이메일·번호·주소)만 쓴다.

| 파일 | 대상 | 기대 |
|---|---|---|
| `input_injection.txt` | 입력 | 차단 (인젝션·탈옥·역할 바꾸기) |
| `input_extraction.txt` | 입력 | 차단 (시스템 프롬프트 추출) |
| `input_others_info.txt` | 입력 | 차단 (타인 정보 요청) |
| `input_out_of_scope.txt` | 입력 | 차단 (서비스 범위 밖) |
| `input_pii.txt` | 입력 | 통과하되 개인정보 마스킹 |
| `input_benign.txt` | 입력 | 그대로 통과 (오탐 측정) |
| `output_block.txt` | 출력 | 차단 (내부 정보·HTML·링크·쓰기 동작 안내·숫자 레이팅) |
| `output_pii.txt` | 출력 | 통과하되 개인정보 마스킹 |
| `output_benign.txt` | 출력 | 그대로 통과 (오탐 측정) |
| `known_bypass.txt` | 입력 | 규칙은 통과, **LLM 분류**가 차단 |
| `holdout_attacks.txt` | 입력 | 차단 — 시험지 |
| `holdout_benign.txt` | 입력 | 통과 — 시험지(오탐) |

- `input_*`·`output_*`은 **규칙만으로** 기대대로 판정돼야 한다 → pytest 회귀 테스트 (`test_chat_guard.py`, LLM 분류기는 꺼 둠).
- `known_bypass`·`holdout_*`은 LLM 분류까지 붙인 실제 평가로만 잰다: `uv run python -m tests.security.test_chat_guard`.
- **`holdout_*`에 맞춰 규칙이나 분류 프롬프트를 고치지 않는다.** 고쳤다면 그 세트는 시험지 역할을 잃었으니 새로 써서 바꾼다.
- 새 우회를 찾으면 `docs/security/findings/`에 기록하고, 규칙으로 막으면 `input_*`에, LLM이 막으면 `known_bypass.txt`에 둔다.
