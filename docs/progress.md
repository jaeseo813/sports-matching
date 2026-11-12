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
| 프론트 | 로그인 필수 구간, 가입·온보딩, 대시보드, 매치 목록·상세·신청·개설, 신청자 수락·거절, 내 정보까지 실제 API 연결 | 풋살 페이지 매치는 mock, 농구 페이지는 `Jason` 브랜치(PR 전) |
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
| 내 활동 | `GET /me/summary`(참가 예정·완료 수, 매너 점수), `GET /me/matches`(참가 예정 매치), `GET /me/venues?sport=`(내 활동 지역 근처 구장) | 로그인, 항상 본인만. 구장 검색 좌표는 서버에 저장된 기준점만 쓴다 |
| 종목 | `GET /sports`(팀 인원·포지션·티어 설명) | 로그인 |

### 동작 규칙 요약
- **정원**은 서버가 계산한다(종목 규칙의 팀 수 × `team_size`). 주최자는 개설 시 수락된 참가자로 자동 등록되어 정원에 포함된다.
- **수락**은 `SELECT ... FOR UPDATE`로 같은 매치를 직렬화해 정원 초과를 막는다.
- **상태**: `open ↔ full → confirmed → playing → completed`, 어느 단계에서든 `canceled`(진행 중 이후는 불가).
- **매치 응답**: `is_host`로 요청자가 주최자인지만 알려 준다(주최자 id는 노출하지 않는다). 주최자가 연 매치는 `my_status=accepted`.
- **추천**: `total = w_dist·S_dist + w_skill·S_skill + w_time·S_time + w_host·S_host + w_fill·S_fill`. 가중치는 DB `matching_weights`의 활성 행, 없으면 0.35/0.30/0.20/0.10/0.05. 응답에 `score`·`breakdown`·`reasons`가 항상 포함된다. 하드 필터: 2시간 이내 시작, 성별 정책, 이미 신청/거절, 시간 겹침, 차단한 주최자.
- **레이팅**: 한 경기의 리뷰를 한 번의 rating period로 묶는다. 같은 쌍 30일 내 1회, 리뷰 제출률 50% 미만이면 보류(`rated_at` 미설정, 재시도 가능), 경기당 ±80 상한. 매너 점수는 레이팅과 분리한다.
- **개인정보**: 응답에 숫자 레이팅·좌표·이메일을 싣지 않는다. 티어 배지와 추이, 거리는 "약 N km" 반올림만 노출한다.

## 프론트 (`frontend/src`)
- 배드민턴 종목 페이지(`sports/badminton/`): 인원 구성, 티어 1~5 설명, 규칙 FAQ. 매치 목록은 공통 `MatchList`(실제 API)로 바꿨고 mock과 상세 모달은 제거했다.
- 공통: `SportPicker`(대시보드·매치 페이지), `AppLayout` 위쪽 여백, `MatchCard`의 참가 단계 표시.
- 풋살 종목 페이지(`sports/football/`): 배드민턴과 같은 구성에 5:5·6:6 필터와 소개 영역(경기장 라인)이 추가됐다. 매치는 mock(`data.ts`). 종목 표시 이름은 "풋살".
- 농구 페이지(`sports/basketball/`)는 `main`에는 아직 "준비 중" 화면이다. 팀원(darelljay)이 `origin/Jason` 브랜치(2026-11-08, 커밋 2개)에 작성했고 **PR은 아직 없다**. 인원 구성(3:3·5:5), 포지션 5개, 티어 1~5, mock 매치 3개, FAQ 6개를 담았다. `main`과 충돌 없음(병합 시뮬레이션으로 확인).
- API 클라이언트(`lib/api/client.ts`): access 토큰은 메모리, refresh 토큰은 localStorage(`teamup.refresh`). 401이면 refresh를 한 번만 하고 재시도한다. 오류는 `ApiError(code, message, fields)`로 바꾼다.
- 인증(`lib/auth.tsx`, `/login`, `/signup`): 가입 후 자동 로그인, 새로고침 시 세션 복구, 로그아웃 시 서버 refresh 무효화. 헤더에 닉네임·로그아웃.
- **로그인 필수 구간**(`RequireAuth`): 비로그인은 시작 화면(`/`)·`/login`·`/signup`만. 나머지 주소는 로그인 화면으로 보내고 로그인 후 원래 주소로 돌아온다. 직접 로그아웃하면 시작 화면으로 간다(다음 사용자가 이전 사용자의 페이지로 돌아가지 않게).
- 시작 화면: 비로그인은 "로그인 / 시작하기(가입)", 로그인하면 "○○님의 대시보드". "매치 찾기"·종목 타일은 가드를 거친다.
- 온보딩(`/onboarding`): 가입 직후 이동. 종목(복수) → 종목별 자기평가 티어·경력(티어 설명은 `GET /sports`) → 활동 지역(구 단위 후보 + 이동 거리). 내 정보에서 다시 들어와 수정할 수 있다. 정확한 현재 위치는 받지 않는다.
- 대시보드: 활동 요약·참가 예정 매치·추천(등록한 종목별 추천을 점수순 상위 3개, 추천 이유 칩). 온보딩 전이면 설정 안내 버튼. 카드를 누르면 상세로 간다.
- 매치(`/matches`, `/matches/:id`, `/matches/new`): 종목 탭 목록 → 상세 페이지(모달 아님) → 신청·신청 취소. 주최자는 상세에서 신청자 수락·거절, 매치 취소. 매치 열기는 내 활동 지역 근처 구장 중에서 고르고 정원은 서버가 정한다.
- 내 정보(`/me`): 닉네임·이메일, 종목별 티어 배지·설명·추이(↑/→/↓), 활동 지역, 로그아웃.
- 공통 코드: `lib/useApi.ts`(GET 훅), `lib/sports.ts`(종목 규칙 캐시), `lib/labels.ts`(상태 문구), `components/MatchList.tsx`(종목 페이지에서도 쓰는 목록).
- **없는 것**: 경기 진행(확정·시작·종료), 팀 분배, 출석, 상호 평가 화면. 구장 등록(관리자) 화면. TanStack Query(`pnpm`이 없어 의존성 추가를 미룸, 지금은 `useEffect`로 불러온다).
- refresh 토큰을 localStorage에 두는 것은 XSS 시 탈취될 수 있다. 위협 모델에 기록하고 Red 단계 소재로 쓴다.

## 테스트·검증
- pytest 231개, ruff, mypy(strict), bandit(`-ll`) 통과. CI(check, gitleaks)는 백엔드를 바꾼 PR에서만 돈다(프론트 CI는 없음). CI는 MariaDB 서비스(`teamup_test`)를 띄워 DB 테스트까지 모두 돌리고, 건너뛴 테스트가 하나라도 있으면 실패한다(DB 연결 실패를 놓치지 않게).
- DB가 필요한 테스트는 **테스트 전용 DB(`teamup_test`, `Settings.test_database_url`)**를 쓰고 항상 롤백한다. 개발 DB(`teamup`)의 데이터와 섞이지 않는다. pytest 시작 시 테스트 DB에 마이그레이션을 자동 적용한다.
- DB 서버에 연결할 수 없으면 DB 테스트는 건너뛴다(컨테이너가 꺼져 있으면 조용히 건너뛰므로 `docker compose up -d db` 후 확인할 것).
- 테스트 DB 주소가 `_test`로 끝나지 않거나 개발 DB와 같으면 pytest가 시작 전에 멈춘다.
- **기존 DB 볼륨이면 테스트 DB를 한 번 만들어야 한다**(pytest가 안내 메시지와 함께 멈춘다). 레포 루트에서:
  `docker compose exec -T db sh -c 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD"' < docker/db-init/01-test-db.sql`
  새로 만든 볼륨은 `docker/db-init/`이 자동으로 실행한다. `.env`의 DB 비밀번호를 바꿨다면 `TEST_DATABASE_URL`도 `.env`에 넣는다(`.env.example` 참고).
- 프론트는 `tsc --noEmit`·`vite build`만 있다(lint·test 스크립트 없음). 화면 흐름은 실서버 + 헤드리스 Chrome으로 수동 확인했다(가입 → 온보딩 → 개설 → 다른 사용자 신청 → 주최자 수락 → 대시보드 반영).
- 보안 회귀 테스트: `tests/security/`
  - 인증: `alg=none` 위조, 잘못된 서명, refresh 토큰의 access 사용, refresh 재사용 시 family 폐기, 로그인 레이트리밋
  - 인가: 비로그인 401, 주최자 전용 403, 다른 매치의 신청 id 접근 404, 타인의 신청 취소·차단 목록 접근 불가
  - 입력: 알 수 없는 종목·필드 거부, 좌표 범위, SQL 인젝션 문자열 거부, 응답에 개인정보 없음

## 의도적 취약점 (보안 학습용)
- **비밀번호 원문 저장** (`core/security.py`의 `hash_password`/`verify_password`). 팀 결정이며 AGENTS.md 5절에 명시했다. Red 단계에서 재현하고 Blue 단계에서 argon2로 교체한다. 외부 공개 배포 금지, 더미 데이터만 사용.

## 알려진 한계 / 남은 일

### 코어
- 관리자를 만드는 방법이 없다. 구장 등록(`POST /venues`)이 관리자 전용이라 지금은 DB에서 `users.role`을 직접 `admin`으로 바꾸거나 스크립트로 구장을 넣어야 한다. 구장이 없으면 매치를 열 수 없다.
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
- 종목 이름은 "풋살"로 통일했다(id는 `football` 유지). 풋살 폴더 `Page.tsx` 첫 줄 주석의 "축구/풋살"은 담당자 영역이라 남겨 두었다.
- 농구 포지션을 팀 분배에 쓸지는 **보류**(농구 `RULES` TODO와 함께 결정).
- 풋살 페이지 매치는 아직 mock(날짜가 고정 문자열). 담당자가 `data.ts`의 mock 대신 공통 `<MatchList sport="football" />`을 넣으면 된다. 농구도 같다.

### 프론트 연결 (다음 작업)
1. ~~`lib/api` 클라이언트(access 토큰 첨부, 401 시 refresh)~~ 완료. TanStack Query 도입은 남음
2. ~~가입·로그인 화면과 토큰 저장~~ 완료
3. ~~온보딩 3단계(종목 / 자기평가 / 활동 지역+거리)~~ 완료
4. ~~배드민턴 페이지 mock을 실제 매치 목록·상세·신청으로 교체~~ 완료. 풋살·농구는 담당자 몫
5. ~~대시보드 추천을 `GET /matches/recommended`로 교체, 추천 이유 칩~~ 완료. breakdown 표시는 남음
6. ~~매치 개설, 신청자 수락·거절~~ 완료. 경기 진행(확정·시작·종료), 팀 구성, 출석, 리뷰 제출 화면은 남음
- 상세는 별도 페이지(`/matches/:id`)로 옮겨 "피드 → 상세 → 신청 3탭"을 지킨다.
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

### 화면 확인용 시드 데이터
화면은 코드 속 mock이 아니라 개발 DB에 넣은 더미로 확인한다(실제 API 경로가 함께 검증된다).
```bash
cd backend && uv run python -m scripts.seed_dev          # 시드를 지우고 다시 넣는다
cd backend && uv run python -m scripts.seed_dev --clear  # 시드만 지운다 (빈 상태 화면 확인)
```
- 구장 6곳(이름 끝 "(시드)"), 사용자 8명(`s1`~`s8@seed.teamup.test`, 비밀번호 `password123`), 매치 8개(종목별, 신청·수락·승인 대기·정원 마감 포함).
- 매치 날짜는 실행 시점 기준 "N일 뒤"로 계산하므로 다시 실행하면 지난 경기가 되지 않는다.
- 시드가 아닌 데이터는 건드리지 않는다. `ENV=local`의 개발 DB에서만 돌고, 테스트 DB에는 넣지 않는다.
- 시드 사용자는 동대문·성북·강남·마포 기준점이라, 내 계정도 온보딩에서 이 지역을 고르면 추천에 시드 매치가 나온다.

`uv`가 없으면 `.venv/bin/<도구>`로 직접 실행할 수 있다. 의존성(`pyjwt`)을 추가했다면 `uv lock`으로 `uv.lock`을 갱신해야 한다.
