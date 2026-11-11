# 진행 현황 (2026-11-11 기준)

`main`에 머지된 PR #1~#16 기준. 백엔드 코어 API는 끝났고, 프론트 연결이 다음 단계다.

## 한눈에 보기

| 영역 | 상태 | 비고 |
|---|---|---|
| 백엔드 뼈대·CI·DB 스키마 | 완료 | PR #2, #4, #5 |
| 인증 | 완료 | 비밀번호 원문 저장(의도적 취약점, 아래 참고) |
| 구장·공간 쿼리 | 완료 | 인덱스 `EXPLAIN` 미확인 |
| 매치·신청·상태 전이 | 완료 | 정원 경합 동시성 테스트 미작성 |
| 추천 스코어링 | 완료 | 순수 함수 + API 연결 |
| 레이팅(상호 평가) | 완료 | Glicko-2 변형, 논문 예제로 검증 |
| 팀 밸런서 | 완료 | 2팀 기준 |
| 종목 규칙·FAQ(백엔드) | 풋살·배드민턴 완료, 농구 진행 중 | 농구는 `Jason` 브랜치(PR 전), `RULES` 미완 |
| 프론트 | 가입·로그인, 대시보드 API 연결 완료. 배드민턴·풋살 페이지, 종목 선택 완료 | 종목 페이지 매치는 mock, 농구 페이지는 `Jason` 브랜치(PR 전) |
| 챗봇 | 미착수 | |
| 보안 진단·방어(Red/Blue) | 미착수 | 회귀 테스트 일부는 이미 있음 |

## 머지된 PR

| # | 내용 |
|---|---|
| 1~5 | 협업 설정, 백엔드 뼈대(FastAPI, Alembic, docker-compose, CI), DB 스키마, 규칙 문서(AGENTS.md), CI Alembic head 검사 |
| 7 | 풋살 규칙·티어 설명·FAQ (팀원) |
| 8 | 배드민턴 종목 페이지, 종목 선택 컴포넌트(`SportPicker`), 공통 여백, 매치 카드 참가 단계 |
| 9 | 배드민턴 규칙(단식/복식)·티어 설명·FAQ |
| 10 | 인증 API |
| 11 | 알고리즘 3종(레이팅, 추천 스코어링, 팀 밸런서) |
| 12 | 구장 반경 검색, 매치 개설·신청·상태 전이 |
| 13 | 온보딩·추천·팀 분배·경기 진행 API |
| 14 | 출석·상호 평가·레이팅 반영, 선호 시간대·차단, 스키마 변경(`rated_at`, `preferred_slots`, `user_blocks`) |
| 15 | 진행 현황 문서 |
| 16 | 풋살 종목 페이지(인원 구성, 티어 설명, 매치 목록·상세, FAQ), 종목 이름 "축구/풋살" → "풋살" (팀원) |

## 백엔드 API (`/api/v1`)

| 영역 | 엔드포인트 | 권한 |
|---|---|---|
| 인증 | `POST /auth/signup`, `login`, `refresh`, `logout`, `GET /auth/me` | 가입·로그인은 공개, 로그인 5/분 |
| 온보딩 | `PUT /me/skills/{sport}`, `PUT/DELETE /me/locations/{slot}`, `PUT /me/preferences`, `PUT/DELETE /me/blocks/{id}` + 각 `GET` | 로그인 |
| 구장 | `GET /venues/nearby`, `GET /venues/{id}`, `POST /venues` | 조회는 로그인, 등록은 관리자 |
| 매치 | `POST /matches`, `GET /matches`, `GET /matches/{id}` | 로그인 |
| 추천 | `GET /matches/recommended?sport=` | 로그인 |
| 신청 | `POST/DELETE /matches/{id}/apply`(10/분), 주최자: `GET .../participations`, `POST .../participations/{pid}/accept·reject` | 주최자 전용 구간 있음 |
| 진행 | `POST /matches/{id}/confirm·start·complete·cancel` | 주최자 |
| 팀 | `POST .../teams/balance`, `GET .../teams`, `PUT .../teams` | 분배·수정은 주최자, 조회는 참가자 |
| 평가 | `PUT .../attendance`(주최자), `POST .../reviews`(참가자), `POST .../rate`(주최자, 1회) | |
| 내 활동 | `GET /me/summary`(참가 예정·완료 수, 매너 점수), `GET /me/matches`(참가 예정 매치) | 로그인, 항상 본인만 |

### 동작 규칙 요약
- **정원**은 서버가 계산한다(종목 규칙의 팀 수 × `team_size`). 주최자는 개설 시 수락된 참가자로 자동 등록되어 정원에 포함된다.
- **수락**은 `SELECT ... FOR UPDATE`로 같은 매치를 직렬화해 정원 초과를 막는다.
- **상태**: `open ↔ full → confirmed → playing → completed`, 어느 단계에서든 `canceled`(진행 중 이후는 불가).
- **추천**: `total = w_dist·S_dist + w_skill·S_skill + w_time·S_time + w_host·S_host + w_fill·S_fill`. 가중치는 DB `matching_weights`의 활성 행, 없으면 0.35/0.30/0.20/0.10/0.05. 응답에 `score`·`breakdown`·`reasons`가 항상 포함된다. 하드 필터: 2시간 이내 시작, 성별 정책, 이미 신청/거절, 시간 겹침, 차단한 주최자.
- **레이팅**: 한 경기의 리뷰를 한 번의 rating period로 묶는다. 같은 쌍 30일 내 1회, 리뷰 제출률 50% 미만이면 보류(`rated_at` 미설정, 재시도 가능), 경기당 ±80 상한. 매너 점수는 레이팅과 분리한다.
- **개인정보**: 응답에 숫자 레이팅·좌표·이메일을 싣지 않는다. 티어 배지와 추이, 거리는 "약 N km" 반올림만 노출한다.

## 프론트 (`frontend/src`)
- 배드민턴 종목 페이지(`sports/badminton/`): 인원 구성, 티어 1~5 설명, 매치 목록·상세 모달, 규칙 FAQ. 매치 데이터는 mock.
- 공통: `SportPicker`(대시보드·매치 페이지), `AppLayout` 위쪽 여백, `MatchCard`의 참가 단계 표시.
- 풋살 종목 페이지(`sports/football/`): 배드민턴과 같은 구성에 5:5·6:6 필터와 소개 영역(경기장 라인)이 추가됐다. 매치는 mock(`data.ts`). 종목 표시 이름은 "풋살".
- 농구 페이지(`sports/basketball/`)는 `main`에는 아직 "준비 중" 화면이다. 팀원(darelljay)이 `origin/Jason` 브랜치(2026-11-08, 커밋 2개)에 작성했고 **PR은 아직 없다**. 인원 구성(3:3·5:5), 포지션 5개, 티어 1~5, mock 매치 3개, FAQ 6개를 담았다. `main`과 충돌 없음(병합 시뮬레이션으로 확인).
- API 클라이언트(`lib/api/client.ts`): access 토큰은 메모리, refresh 토큰은 localStorage(`teamup.refresh`). 401이면 refresh를 한 번만 하고 재시도한다. 오류는 `ApiError(code, message, fields)`로 바꾼다.
- 인증(`lib/auth.tsx`, `/login`, `/signup`): 가입 후 자동 로그인, 새로고침 시 세션 복구, 로그아웃 시 서버 refresh 무효화. 헤더에 닉네임·로그아웃.
- 대시보드: 활동 요약·참가 예정 매치·추천(등록한 종목별 추천을 점수순으로 상위 3개)을 실제 API로 보여준다. 비로그인·온보딩 전·빈 목록 상태 문구가 있다.
- **없는 것**: 온보딩 화면, 매치 개설·신청 화면, TanStack Query(`pnpm`이 없어 의존성 추가를 미룸, 지금은 `useEffect`로 불러온다).
- refresh 토큰을 localStorage에 두는 것은 XSS 시 탈취될 수 있다. 위협 모델에 기록하고 Red 단계 소재로 쓴다.

## 테스트·검증
- pytest 225개, ruff, mypy(strict), bandit(`-ll`) 통과. CI(check, gitleaks)는 백엔드를 바꾼 PR에서만 돈다(프론트 CI는 없음).
- DB가 필요한 테스트는 실제 MariaDB를 쓰고 항상 롤백한다. DB에 연결할 수 없으면 건너뛴다(컨테이너가 꺼져 있으면 조용히 건너뛰므로 `docker compose up -d db` 후 확인할 것).
- 보안 회귀 테스트: `tests/security/`
  - 인증: `alg=none` 위조, 잘못된 서명, refresh 토큰의 access 사용, refresh 재사용 시 family 폐기, 로그인 레이트리밋
  - 인가: 비로그인 401, 주최자 전용 403, 다른 매치의 신청 id 접근 404, 타인의 신청 취소·차단 목록 접근 불가
  - 입력: 알 수 없는 종목·필드 거부, 좌표 범위, SQL 인젝션 문자열 거부, 응답에 개인정보 없음

## 의도적 취약점 (보안 학습용)
- **비밀번호 원문 저장** (`core/security.py`의 `hash_password`/`verify_password`). 팀 결정이며 AGENTS.md 5절에 명시했다. Red 단계에서 재현하고 Blue 단계에서 argon2로 교체한다. 외부 공개 배포 금지, 더미 데이터만 사용.

## 알려진 한계 / 남은 일

### 코어
- 관리자를 만드는 방법이 없다. 구장 등록(`POST /venues`)이 관리자 전용이라 지금은 DB에서 `users.role`을 직접 `admin`으로 바꿔야 한다.
- 토큰 저장소(refresh)와 레이트리밋이 **인메모리**다. 서버를 재시작하면 로그아웃되고 워커가 여러 개면 재사용 감지가 어긋난다. Redis로 교체해야 한다.
- 정원 경합을 **동시 요청**으로 검증하지 못했다(테스트가 단일 연결).
- 구장 SPATIAL INDEX를 실제로 쓰는지 `EXPLAIN`으로 확인하지 못했다(개발 DB에 구장이 없었음).
- 로그인 실패·권한 거부의 보안 이벤트 로깅, 로그 마스킹, 입력 이상 탐지는 없다.
- 탈퇴 API와 리뷰 익명화가 없다. 대화 이력 삭제 등 개인정보 규칙도 미구현.
- 지오코딩, 매치룸 채팅, 알림은 없다(채팅·알림은 버리는 순서에 있음).
- 팀이 3개 이상이면 밸런서가 국소 최적에서 멈출 수 있다(모든 종목이 2팀이라 일반화하지 않음).

### 종목
- 농구는 `origin/Jason` 브랜치의 작업을 PR로 올려 리뷰·머지해야 한다(브랜치명도 `feat/<이슈번호>-<설명>` 규칙에 맞게 정리). 그 브랜치를 읽고 확인한 문제:
  - 백엔드 `app/sports/basketball/__init__.py`는 그대로다. `RULES`의 TODO(포지션 사용 여부, `tier_labels`)가 남았고 새 `faq.py`는 `__all__`에 노출되지 않아 어디서도 쓰이지 않는다. 테스트도 없다.
  - 백엔드 `faq.py`(규칙 6개: 인원, 3점슛, 자유투, 파울, 더블 드리블, 아웃)와 프론트 `data.ts`의 `faq`(운영 6개: 인원, 포지션, 티어, 초보자, 인원 부족, 포지션 변경)가 서로 다른 내용인데, docstring은 "같은 내용을 유지한다"고 적혀 있다.
  - 프론트 티어 문구는 `data.ts`에만 있고 백엔드에 대응하는 `tier_labels`가 없다.
  - 프론트 `data.ts`는 타입이 없고(매치 `id`가 문자열, `format`이 `"3대3"` 문자열) 매치 카드에 `{...m}`을 통째로 넘긴다. 풋살처럼 타입을 정해 필요한 값만 넘기는 편이 안전하다. typecheck는 확인하지 못했다.
  - 포지션을 프론트에서 쓰는데 백엔드 `RULES`는 포지션을 다루지 않아, 팀 분배의 포지션 제약과 어떻게 연결할지 정해야 한다.
  - 포지션 설명에 실존 선수 이름이 들어 있고, mock 구장은 실제 지역명(수원·용인·성남)을 쓴다. 더미 데이터 규칙(실명·실주소 금지)에 비춰 정리를 검토한다.
- 풋살·배드민턴 티어 문구·FAQ가 프론트 `data.ts`와 백엔드 `faq.py`에 중복되어 있다(풋살은 FAQ 7개·티어 5개 문구가 일치함을 대조로 확인). API로 내려주기 전까지 두 곳을 함께 고쳐야 한다.
- 종목 표시 이름이 "풋살"로 바뀌었다. 백엔드는 이 이름에 의존하지 않지만, 소개 문구(`pages/Home.tsx`), `README.md`, `AGENTS.md`에는 "축구/풋살"이 남아 있어 통일 여부를 정해야 한다.
- 풋살·배드민턴 mock 매치의 날짜가 고정 문자열이라 API 연동 전에는 지난 날짜로 보인다.

### 프론트 연결 (다음 작업)
1. ~~`lib/api` 클라이언트(access 토큰 첨부, 401 시 refresh)~~ 완료. TanStack Query 도입은 남음
2. ~~가입·로그인 화면과 토큰 저장~~ 완료
3. 온보딩 3단계(종목 / 자기평가 / 활동 지역+거리) → `PUT /me/skills`, `PUT /me/locations`
4. 배드민턴·풋살 페이지의 mock을 `GET /matches`, `GET /matches/{id}`, `POST /matches/{id}/apply`로 교체
5. ~~대시보드 추천을 `GET /matches/recommended`로 교체, 추천 이유 칩~~ 완료. breakdown 표시는 남음
6. 매치 개설, 신청자 승인, 팀 구성, 리뷰 제출 화면
- 상세 화면은 지금 모달이다. "피드 → 상세 → 신청 3탭" 원칙에 맞게 별도 페이지로 옮길지 정해야 한다.
- 로컬 개발 서버(Vite)는 `pnpm`이 없어서 `npx vite`로 띄웠다. 프론트 `lint`·`test` 스크립트도 아직 없다.

### 그 뒤
- 챗봇(`services/chatbot.py`, SSE, 읽기 전용 도구)
- 보안 진단(Red)과 방어(Blue): 취약점 리포트, STRIDE 위협 모델(`docs/security/threat-model.md`, 아직 없음), 라이브 데모, 체크리스트

## 로컬 실행 메모
```bash
docker compose up -d db                # DB (꺼져 있으면 DB 테스트가 조용히 건너뛰어진다)
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
cd backend && uv run pytest -q && uv run ruff check . && uv run mypy app
cd frontend && pnpm install && pnpm dev   # pnpm이 없으면 npx vite
```
`uv`가 없으면 `.venv/bin/<도구>`로 직접 실행할 수 있다. 의존성(`pyjwt`)을 추가했다면 `uv lock`으로 `uv.lock`을 갱신해야 한다.
