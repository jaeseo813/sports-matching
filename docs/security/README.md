# 보안 파트 안내

보안은 세 파트로 나눠 맡는다. 담당자는 정해지면 아래 표에 적는다.

| 파트 | 담당 | 주 작업 위치 |
|---|---|---|
| A. 챗봇 가드레일 | (미정) | `backend/app/services/chat_guard.py`, `backend/tests/security/test_chat_*.py` |
| B. 보안 대시보드 (Grafana) | 송수한 | `infra/monitoring/`(새로 만듦), `docker-compose.yml`의 `monitoring` 프로필 |
| C. RBAC 정책 | (미정) | `backend/app/api/deps.py`, `backend/app/services/*`의 권한 검사, `docs/security/rbac.md`(새로 만듦) |

## 세 파트를 잇는 약속: 보안 이벤트

세 파트는 **보안 이벤트 하나로 연결된다**. A·C가 이벤트를 남기고 B가 그걸 그린다.

- 기록: `app/core/security_events.py`의 `record_security_event(event, code, route)`
  - Prometheus 카운터 `teamup_security_events_total{event, code, route}`를 올리고, `teamup.security` 로거에 한 줄 남긴다.
  - `event`는 Literal로 고정: `unauthorized`, `forbidden`, `rate_limited`, `chat_input_blocked`, `chat_output_blocked`.
    새 종류를 추가하면 Literal과 대시보드를 같은 PR에서 고친다.
  - `code`는 사유 코드(`INVALID_CREDENTIALS`, `FORBIDDEN`, `PROMPT_INJECTION` 등), `route`는 `/matches/{match_id}` 같은 템플릿(`/api/v1` 제외).
  - **원문 입력·토큰·이메일·좌표는 넘기지 않는다.** 라벨 값 종류가 무한히 늘어나도 안 된다(사용자 id, 매치 id 금지).
- 401·403·429는 `app/main.py`의 예외 처리기가 **자동으로** 남긴다. 서비스 코드에서 따로 부를 필요 없다.
- 수집: `GET /metrics` (Prometheus 형식). `.env`의 `METRICS_TOKEN`이 있으면 `Authorization: Bearer <값>`이 맞아야 하고, 비어 있으면 `ENV=local`에서만 열린다(B 절 "/metrics 보호").
- 테스트: `tests/security/test_security_events.py`

## A. 챗봇 가드레일

**목표**: 챗봇 입력·출력에 가드를 세우고, 공격 문장 세트로 우회 시도 → 보강 → 재검증한다 (AGENTS.md 5절).

**지금 있는 것** (v2 결합: 입력은 규칙 → LLM 분류, 출력은 규칙)
- `services/chat_guard.py`: `check_input(text)`, `check_output(text)` → `GuardResult(allowed, text, code)`.
  두 함수는 `async`다(LLM 판정이 들어올 수 있게). **함수 모양은 유지하고 안쪽만 바꾼다** — 챗봇 쪽이 이 두 함수만 부른다.
  - 입력 차단: `TOO_LONG`, `PROMPT_EXTRACTION`, `PROMPT_INJECTION`, `OTHERS_INFO`, `OUT_OF_SCOPE` / 마스킹 후 통과: `PII_INPUT`
  - 출력 차단: `PROMPT_LEAK`, `HTML`, `LINK`, `RATING_LEAK`, `WRITE_CLAIM` / 마스킹 후 통과: `PII_OUTPUT`
  - 입력은 규칙을 통과하면 DeepSeek으로 한 번 더 분류한다(마스킹한 값만). 키가 없으면 규칙만, 분류 실패는 차단(`GUARD_UNAVAILABLE` → 챗봇은 필터 UI로 degrade).
  - 차단·마스킹 모두 `record_security_event("chat_input_blocked" | "chat_output_blocked", code)` → 대시보드 "챗봇 가드 차단 사유별" 패널.
- 챗봇(`services/chatbot.py`): user 이력은 메시지마다 입력 가드를 거친다. assistant 이력은 서버가 답과 함께 준 서명(`sig`)이 맞을 때만 받는다(위조 방지). 사용자당 24시간 토큰 상한이 있다(`DAILY_TOKEN_LIMIT`).
- 공격 세트 `backend/tests/security/chat_attacks/`(규칙 세트, LLM이 맡는 `known_bypass`, 시험지 `holdout_*` — 쓰는 법은 그 폴더 README), 회귀 테스트 `tests/security/test_chat_guard.py`(pytest에서는 LLM 분류기를 끈다).
- 실제 평가: `cd backend && uv run python -m tests.security.test_chat_guard` (DeepSeek 호출, 1분쯤).
- 실제 챗봇 공격: `uv run python -m tests.security.redteam_chat 결과.json` (시드 데이터 필요, 3분쯤). 입력 가드를 끈 모드도 함께 돌려 다층 방어를 본다. 결과 [findings/002](findings/002-chatbot-live-redteam.md).
- 평가 표 [chat-guard-eval.md](chat-guard-eval.md), 우회 기록 [findings/001](findings/001-rule-guard-bypass.md).

**남은 할 일**
1. Red 계속: 공격 세트와 여러 턴 시나리오를 키운다(지금은 공격 약 80개, 여러 턴 5개). 결과는 `findings/NNN-*.md`.
2. 출력 가드는 표지 문구 검사라 바꿔 말한 프롬프트 노출을 못 잡는다. 지금은 시스템 프롬프트와 입력 분류기, 두 겹이 막는다. 필요하면 출력에도 LLM 분류를 붙여 비교한다.
3. ~~챗봇 전체 요청 수 카운터~~ → B에서 추가함(`teamup_chat_requests_total`, 가드 검사 수 `teamup_chat_guard_checks_total`). `check_input`·`check_output` 첫 줄의 `count_guard_check`는 지우지 않는다(차단율의 분모).
4. 대화 이력 30일 보관·탈퇴 시 삭제는 #31(배포 준비)에서 정한다.

## B. 보안 대시보드 (Grafana)

**목표**: 보안 이벤트를 한눈에 보는 대시보드. 발표 라이브 데모(공격 → 그래프에 바로 뜸)에 쓴다.

**지금 있는 것**
- `docker-compose.yml`의 `monitoring` 프로필에 Prometheus(`127.0.0.1:9090`)·Grafana(`127.0.0.1:3000`). 설정은 `infra/monitoring/`.
- Prometheus는 5초마다 `host.docker.internal:8000/metrics`(로컬 uvicorn)를 수집한다(job `teamup-api`). Grafana 데이터소스 uid는 `teamup-prometheus`.

**실행**
```bash
# 1) API를 로컬에서 띄운다 (9절)
cd backend && uv run uvicorn app.main:app --reload
# 2) 모니터링 스택
docker compose --profile monitoring up -d
```
- Grafana: http://127.0.0.1:3000 , 아이디 `admin`, 비밀번호는 `.env`의 `GRAFANA_ADMIN_PASSWORD`(없으면 `change-me`). 익명 접속은 꺼져 있다.
  비밀번호는 **Grafana를 처음 띄울 때만** 적용되므로 `.env`에 먼저 넣고 띄운다. 이미 띄운 뒤 바꾸려면:
  `docker compose exec grafana grafana cli admin reset-admin-password <새 비밀번호>`
  (`docker compose down -v`는 쓰지 않는다 — DB 볼륨 `db_data`까지 지워진다.)
- 수집 확인: http://127.0.0.1:9090/targets 에서 `teamup-api`가 `UP`. API가 꺼져 있으면 `DOWN`이고, 대시보드는 "API 수집 상태"가 빨간 "수집 중단", 나머지 패널은 비거나 "데이터 없음"이 된다.
- **Linux(Docker Desktop이 아닌 Docker Engine)**: 컨테이너가 호스트의 `127.0.0.1`에 닿지 않아 계속 `DOWN`이다. uvicorn을 docker 브리지 주소로 띄운다: `uv run uvicorn app.main:app --reload --host 172.17.0.1` (`ip addr show docker0`로 주소 확인). `0.0.0.0`은 API와 `/metrics`가 같은 네트워크에 열리므로 쓰지 않는다. macOS·Windows(WSL2 포함) Docker Desktop은 그대로 된다.
- 3000번(또는 9090번) 포트를 이미 쓰고 있으면 `docker-compose.yml`에서 **왼쪽 포트만** 바꾼다(예: `127.0.0.1:3001:3000`).
- 끄기: `docker compose stop prometheus grafana` (`--profile monitoring down`은 DB까지 멈춘다)

- 대시보드 **TeamUp 보안 이벤트** (http://127.0.0.1:3000/d/teamup-security, `infra/monitoring/grafana/dashboards/security.json`): 15분 범위, 5초 새로고침.

  | 패널 | 보는 것 |
  |---|---|
  | API 수집 상태 | Prometheus가 API를 수집 중인지. "수집 중단"이면 아래 패널이 비어도 공격이 없는 게 아니다 |
  | 이벤트 종류별 추이 | 1분 동안 생긴 이벤트 수(종류별) |
  | 로그인 실패 (1분) | `INVALID_CREDENTIALS` 수 |
  | 403이 많은 경로 Top 5 | 선택한 범위 동안 403이 많은 route |
  | 레이트리밋 | 429 수(경로별) |
  | 챗봇 가드 차단 사유별 | `chat_input_blocked`·`chat_output_blocked`의 사유 코드별 수 |
  | 챗봇 가드 차단율 | 가드 **검사 기준** 차단 비율(입력·출력). 개인정보 마스킹(`PII_*`)은 따로, 가드 장애(`GUARD_UNAVAILABLE`)는 뺀다. 입력 가드는 요청마다 이력의 사용자 메시지를 전부 다시 검사하므로 입력 차단율은 이력 재검사를 포함한다 — 공격 메시지 수 기준이 아니다(아래 "알려진 한계"). 출력 가드는 새 답만 검사한다 |
  | 챗봇 요청 수 | 로그인·레이트리밋을 통과한 챗봇 요청 수 |

  패널은 모두 `increase()`로 증가량만 그린다(uvicorn `--reload`로 카운터가 0이 돼도 그래프가 꺾이지 않게).
  대시보드는 파일로만 관리한다(화면에서 저장 불가). 고치려면 화면에서 수정 → JSON 내보내기 → 이 파일에 커밋, 데이터소스 uid는 `teamup-prometheus` 유지.
- 경보 규칙 (`infra/monitoring/prometheus/alerts.yml`, 확인은 http://127.0.0.1:9090/alerts): 1분 안에 로그인 실패 5회 이상 `LoginFailureBurst`, 403 10회 이상 `ForbiddenBurst`. 알림 채널(메일·슬랙)은 없다.
  로그인은 IP당 1분 5회 제한이라 한 IP에서는 로그인 실패가 1분에 5회까지만 쌓인다(그 뒤는 `rate_limited`).
- 테스트 `tests/security/test_security_dashboard.py`: 대시보드가 쓰는 `event` 값이 `SecurityEvent` Literal에 있는지, 카운터를 `increase`/`rate`로만 쓰는지, PromQL 괄호 짝, 경보 규칙의 이벤트 이름 등을 검사한다. **Literal의 이벤트 이름을 바꾸면 이 테스트가 실패하니 대시보드와 경보 규칙(`alerts.yml`, 같은 테스트가 검사)도 같이 고친다.**

**라이브 데모** (`infra/monitoring/demo.sh`, 시드 데이터 필요: `cd backend && uv run python -m scripts.seed_dev`)
1. 발표 전: API와 모니터링 스택을 띄우고 `bash infra/monitoring/demo.sh prepare`.
   - Prometheus는 **새로 생긴 시계열의 첫 값은 증가로 세지 않는다**. API를 띄운 뒤 처음 나는 이벤트는 그래프에 안 보이므로, 종류마다 한 번씩 미리 발생시킨다.
   - 로그인 한도(1분 5회)를 본 실행에 남겨 두려고 시드 계정 토큰을 미리 받아 둔다.
2. 1분 뒤, 발표 중: 대시보드를 띄워 두고 `bash infra/monitoring/demo.sh`.
   ① 토큰 없이 `/auth/me` 10회 → 401 ② 틀린 비밀번호 로그인 7회 → 401 ×5, 429 ×2 ③ 남이 연 매치 취소 12회 → 403 ④ 챗봇에 600자 입력 3회 → 입력 가드 `TOO_LONG` 차단(규칙만으로 막혀 DeepSeek를 부르지 않는다. 서버에 `DEEPSEEK_API_KEY`가 없으면 503으로 끝나고 차단율은 비어 있다).
   10초쯤 뒤 패널이 올라가고 `LoginFailureBurst`·`ForbiddenBurst` 경보가 울린다.
3. API를 재시작했다면 1부터 다시 한다.

**/metrics 보호 (토큰)**
- 방식: `.env`의 `METRICS_TOKEN`. API는 `Authorization: Bearer <값>`이 맞을 때만 지표를 준다(비교는 `secrets.compare_digest`). 틀리면 401 `METRICS_UNAUTHORIZED`이고 보안 이벤트(`unauthorized`, route `/metrics`)로도 남는다.
- 비워 두면 `ENV=local`에서만 열리고, `ENV`를 `staging`·`production`으로 둔 서버에서는 항상 401이다. `ENV`의 기본값이 `local`이니 스테이징 서버는 `ENV`를 꼭 지정한다.
- 값은 `openssl rand -hex 32`로 만든다(영문·숫자 64자). `/metrics`에는 레이트리밋이 없어 긴 무작위 값이 유일한 방어이고, `$`·공백이 들어가면 compose와 API가 다르게 읽어 수집이 끊긴다.
- Prometheus는 같은 `.env` 값을 compose가 넘겨 받아 시작할 때 `/prometheus/metrics_token` 파일로 쓰고 그 값으로 수집한다. 토큰은 레포·이미지에는 남지 않지만, 컨테이너 환경변수라 `docker inspect`로는 보인다(로컬 개발용 수준).
- 토큰을 넣거나 바꾸면 **API와 Prometheus를 둘 다 다시 띄운다**(`docker compose --profile monitoring up -d --force-recreate prometheus`). 한쪽만 바꾸면 수집 상태가 "수집 중단"이 되고, 5초마다 401 이벤트가 쌓인다.
- 고른 이유: 내 컴퓨터 요청만 허용하는 방식은 Docker를 거친 요청이 운영체제마다 다른 주소로 보여 깨지기 쉽다. 토큰은 Mac·Windows·Linux에서 같게 동작하고, "토큰 없이 요청하면 막힌다"를 데모로 보일 수 있다.

**알려진 한계 (A와 같이 볼 것)**
- 챗봇은 요청마다 이력의 사용자 메시지를 전부 입력 가드에 다시 넣는다(`chatbot.chat_events`). 그래서 긴 대화일수록 같은 질문이 여러 번 검사·기록되고, 입력 차단율은 공격 메시지 수가 아니라 검사 기준이 된다. (assistant 이력은 #35부터 서명으로 검증하고 출력 가드는 새 답만 본다.)
- 화면(`ChatPanel`)은 막힌 사용자 질문을 이력에 남겨 다음 요청마다 다시 보내서, 한 번 막힌 대화는 계속 막히고 차단 이벤트도 매번 다시 쌓인다.
- 해결 방향: 이력의 사용자 메시지는 기록 없이 검사하고 마지막 메시지만 기록·집계, 화면은 막힌 질문을 이력에서 뺀다. 가드·챗봇 담당(A)이 정할 일이다.

새 보안 이벤트 종류가 생기면 Literal과 대시보드를 같은 PR에서 고친다.

## C. RBAC 정책

**목표**: 누가 무엇을 할 수 있는지 역할·권한 표로 정리하고, 흩어진 검사를 그 표대로 맞춘다.

**지금 상태**
- 전역 역할은 `Role.USER` / `Role.ADMIN` 두 개(`models/enums.py`, `users.role`). `require_admin`은 `POST /venues` 한 곳만 쓴다.
- 엔드포인트 40개: 공개 3개(`/auth/signup`, `/auth/login`, `/health`), 로그인 필요 36개, 관리자 1개.
- **매치 안에서의 역할**(주최자·참가자)은 서비스 코드에서 직접 검사한다:
  - `services/matches.py:225` 주최자만 (신청 수락·거절, 확정·취소·시작·종료 등)
  - `services/teams.py:30` 주최자만 (팀 분배·수정), `services/teams.py:102` 참가자만 (팀 보기)
  - `services/reviews.py:39` 참가자만 (평가), `:72`, `:100` 주최자만 (출석·레이팅 반영)
- 관리자를 만드는 방법이 없다(DB에서 `users.role`을 직접 바꿔야 함).

**할 일**
1. `docs/security/rbac.md`: 역할(비로그인 / 사용자 / 주최자 / 참가자 / 관리자, 필요하면 추가) × 엔드포인트 권한 표.
2. 표와 코드 비교 → 어긋나는 곳 수정. 매치 역할 검사를 한 곳으로 모을지(예: 의존성 `require_match_role`) 결정.
3. 관리자 부여 방법(스크립트 등)과 관리자 권한 범위(매치 강제 취소? 사용자 정지?) 결정.
4. 표의 각 칸을 `tests/security/`에 테스트로: 권한 없는 역할로 호출하면 401/403/404.
5. 챗봇 도구(`search_matches` 등)도 요청자 권한으로만 동작하는지 표에 포함 (A와 연결).

## 공통 규칙
- 보안 테스트는 `backend/tests/security/`. 새 엔드포인트는 인가 의존성 + 보안 테스트 1개 필수(AGENTS.md 9절).
- 공격 실습은 로컬·스테이징에서만, 더미 데이터만.
- 의도적 취약점(비밀번호 원문 저장)은 그대로 둔다. 위협 모델에 기록돼 있다.
