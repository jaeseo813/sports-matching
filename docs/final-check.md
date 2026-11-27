# TeamUp 최종 점검 (2026-11-27)

혼자서도 팀 운동을 할 수 있게 거리·실력으로 매칭하는 웹 서비스. 종목: 풋살·농구·배드민턴.
기준: API는 실제 코드(OpenAPI), 기능은 AGENTS.md. 상태: ✅ 완료 / 🔶 일부 / ❌ 없음

## 1. 기능

| 기능 | 상태 | 비고 |
|---|---|---|
| 가입·로그인 (JWT 24시간) | ✅ | 비밀번호 Argon2 해싱(#39) |
| 온보딩 (종목·자기평가·활동 지역) | ✅ | |
| 매치 목록·상세·개설·신청·수락/거절 | ✅ | 정원은 DB 잠금으로 보호. 동시 요청 테스트 없음 |
| 추천 (점수 + 이유) | ✅ | 화면에는 이유만, 점수 구성(breakdown)은 API만 |
| 팀 자동 분배·수동 조정 | ✅ | |
| 출석·상호 평가·실력 반영 | ✅ | 숫자 레이팅은 노출 안 함, 티어와 추이만 |
| 차단 | ✅ | 매치 상세(주최자)·신청자 명단에서 차단, 내 정보에서 해제. 차단한 주최자의 매치는 추천·목록에서 제외 |
| 선호 시간대 | 🔶 | API만 (화면은 만들지 않기로 함) |
| 챗봇 (찾기·설명·티어·FAQ) | ✅ | 읽기 전용, 신청은 버튼 제안만 |
| 종목 페이지 | ✅ | 풋살·배드민턴·농구(#24) |
| 관리자 구장 등록 | ✅ | 내 정보 → 구장 등록(관리자만). 관리자 지정: `uv run python -m scripts.make_admin <이메일>`. 좌표는 직접 입력 |
| 매칭 알림 | ✅ | 앱 안 알림: 새 신청(주최자), 수락·거절(신청자), 매치 확정(참가자)·취소(참가자와 대기 중인 신청자). 30초마다 확인 |
| 회원 탈퇴 | ✅ | 내 정보 → 회원 탈퇴(비밀번호 확인). 개인정보 삭제, 매치 기록·평가는 이름 없이 보존, 신청은 자동 취소, 주최 중이면 막음 |
| 지도·매치룸 채팅 | ❌ | 하지 않기로 함 |

## 2. API (`/api/v1`, 45개: 공개 3 · 로그인 41 · 관리자 1)

| 영역 | 엔드포인트 | 권한 |
|---|---|---|
| 상태 | `GET /health` | 공개 |
| 인증 | `POST /auth/signup` · `POST /auth/login` | 공개 (로그인 5/분) |
| | `GET /auth/me` | 로그인 |
| 종목 | `GET /sports` | 로그인 |
| 구장 | `GET /venues/nearby` · `GET /venues/{id}` | 로그인 |
| | `POST /venues` | 관리자 |
| 매치 | `GET·POST /matches` · `GET /matches/recommended` · `GET /matches/{id}` | 로그인 |
| 신청 | `POST·DELETE /matches/{id}/apply` | 로그인 (신청 10/분) |
| | `GET /matches/{id}/participations` · `POST …/{pid}/accept` · `POST …/{pid}/reject` | 주최자 |
| 진행 | `POST /matches/{id}/confirm` · `cancel` · `complete` | 주최자 |
| 팀 | `POST /matches/{id}/teams/balance` · `PUT …/teams` | 주최자 |
| | `GET /matches/{id}/teams` | 참가자 |
| 차단 | `PUT /matches/{id}/host-block` (주최자 id를 노출하지 않고 차단) | 로그인 |
| 평가 | `PUT /matches/{id}/attendance` · `POST …/rate` | 주최자 |
| | `GET /matches/{id}/reviews/targets` · `POST …/reviews` | 참가자 |
| 내 정보 | `/me/skills` (GET, PUT) · `/me/locations` (GET, PUT, DELETE) · `/me/preferences` (GET, PUT) · `/me/blocks` (GET, PUT, DELETE) | 본인 |
| 내 활동 | `GET /me/summary` · `GET /me/matches` · `GET /me/venues` | 본인 |
| 알림 | `GET /me/notifications` · `POST /me/notifications/read` | 본인 |
| 탈퇴 | `POST /me/withdraw` (비밀번호 확인, 로그인과 같은 5/분) | 본인 |
| 챗봇 | `POST /chat` (SSE) | 로그인 (20/5분, 24시간 토큰 20만) |

`/api/v1` 밖: `GET /metrics` (`METRICS_TOKEN`, 비우면 local에서만 열림)

## 3. 보안

| 파트 | 상태 | 내용 |
|---|---|---|
| A 챗봇 가드 | ✅ | 입력·출력 모두 규칙 → LLM 분류, 이력 위조 차단, 토큰 상한. finding 5건 |
| B 대시보드 | ✅ | 보안 이벤트·차단율·경보, `/metrics` 토큰 |
| C RBAC | 🔶 | 역할 의존성 `require_roles`/`AdminUser` 추가(#39). **`rbac.md` 권한 표와 역할별 테스트 없음** |

가드 시험지: 입력 공격 35/35 차단, 정상 오탐 0/33 / 출력 공격 14/14 차단, 정상 오탐 0/16.
실제 챗봇 공격 53개: 입력 가드 47개 차단, 6개는 LLM이 거절하거나 안전하게 답함. 정상 질문 33개 모두 답변.
한계: 풋살·한 계정으로만 시험, LLM이라 매번 결과가 다를 수 있음. 상세는 `security/chat-guard-eval.md`.

## 4. 검증
- 알림·차단·구장 등록은 실서버 + 헤드리스 Chrome으로 데스크톱·모바일(375px) 확인
- 백엔드: pytest 572개 통과(건너뜀 없음). CI: ruff, mypy, bandit, pip-audit, gitleaks
- 프론트: 타입 검사 통과. **lint·자동 테스트 없음**

## 5. 배포 전에 할 일

**반드시** (지금 AGENTS.md는 외부 공개 배포를 금지한다)
1. ~~비밀번호 해싱~~ → #39 완료, 기존 원문 계정은 #41 마이그레이션으로 해시
2. ~~AGENTS.md 배포·공격 실습 문구~~ → 완료 (배포는 `deploy.md`대로, 공격 실습은 로컬·스테이징만)
3. ~~운영 설정~~ → 완료: 개발용 값이면 서버가 시작되지 않음, 도커 기본 `ENV=production`, 프록시 IP 처리, `.env.production.example`·`docs/deploy.md`. **실제 비밀 값은 배포하는 쪽에서 넣는다**
4. ~~회원 탈퇴·개인정보 삭제~~ → 완료

**권장**
5. RBAC 권한 표와 테스트
6. 정원 동시 신청 테스트
7. 레이트리밋·토큰 상한이 메모리에 있어 서버 1대로 운영할지 결정

**문서 정리**: `progress.md`는 11월 11일 기준이라 챗봇·보안이 "미착수"로 남아 있다. `security/README.md`의 엔드포인트 수(40개)와 이슈 #31의 체크도 갱신 필요.
