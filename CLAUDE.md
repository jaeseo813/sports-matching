# TeamUp (가칭) — 팀 스포츠 매칭 플랫폼

풋살·농구처럼 인원이 모여야 하는 운동을, 참가자를 **거리·실력 기준으로 매칭**해 혼자서도 할 수 있게 하는 웹 서비스.
**학회 프로젝트**. 목표는 두 가지이며 순서가 있다: ① 서비스를 끝까지 동작시킨다 → ② 그 위에 보안을 직접 공격·방어하며 학습한다 (5절).
일정이 밀리면 기능을 버리고 보안은 지킨다. 서비스명은 가칭 — 확정되면 이 문서와 `app/core/config.py`를 함께 수정.

**1차 지원 종목**: 농구, 축구/풋살, 배드민턴 (프론트 `src/sports/<종목>/` 폴더로 분리, 종목 담당자는 자기 폴더 안에서만 작업, 등록은 `src/sports/registry.ts`).

## 1. 비범위
결제/정산, 네이티브 앱, 구장 예약 연동(구장은 관리자 등록 마스터 데이터), ML 추천(규칙 기반 스코어링만),
**챗봇의 쓰기 동작**(신청·개설·취소 실행 금지 — 읽기 + 버튼 제안까지만), 보안 제품 수준 방어(WAF 등).

## 2. 기술 스택
- 백엔드: Python 3.12, FastAPI(async), MariaDB 11(공간 기능), SQLAlchemy 2.0 async(`asyncmy`) + Alembic, Pydantic v2
- 인증: JWT(access 30분 / refresh 14일), argon2. 캐시·레이트리밋: Redis (없으면 인메모리 degrade)
- 프론트(가정): React 19 + Vite + TS, TanStack Query, Zustand, Tailwind + shadcn/ui, Kakao Maps, react-hook-form + zod
- 챗봇: `anthropic` SDK(`AsyncAnthropic`), 모델 `claude-opus-5-5`(날짜 접미사 금지), SSE 스트리밍, tool use
- 보안 도구: bandit, ruff(S), semgrep, pip-audit, pnpm audit, gitleaks, OWASP ZAP, Burp Community
- 인프라: docker-compose(api, db, redis, web), GitHub Actions(lint + test + 보안 스캔 게이트)

## 3. 구조 규칙
```
backend/app/{core,models,schemas,api/v1,services,repositories}  backend/tests/{services,security}
frontend/src/{pages,features,components/ui,lib/api}            docs/security/{threat-model.md,findings/}
```
- 비즈니스 로직은 `services/`에만. 라우터는 검증 → 서비스 호출 → 응답 변환만.
- 공간 raw SQL은 `repositories/`에만.
- `services/matching.py`, `skill.py`, `balancer.py`는 **DB 없이 테스트 가능한 순수 함수**, 분기 전부 단위 테스트.

## 4. 핵심 도메인
**데이터**: User, UserLocation(활동 기준점 최대 2개, `POINT SRID 4326`, SPATIAL INDEX), UserSkill(종목별 rating/RD),
Venue, Match(status: open→full→confirmed→playing→completed/canceled), Participation, PeerReview, TeamAssignment, `matching_weights`(가중치는 DB에).

**실력 모델**: 승패 Elo 대신 **상호 평가**(`better/similar/worse`)를 Glicko-2 변형으로 반영. 한 경기의 리뷰는 한 번의 rating period로 묶는다.
- 초기값: 자기평가 티어 1~5 → rating 900/1100/1300/1500/1700 + `min(years,5)*15`, RD 300~350
- 어뷰징 방지: 같은 쌍 30일 내 1회만 반영, 리뷰 제출률 50% 미만이면 갱신 보류, 경기당 Δrating ±80 상한
- `manner_flag`는 레이팅과 분리해 `manner_score`로만 반영
- **숫자 레이팅은 사용자에게 노출 금지** — 티어 배지와 ↑/→/↓ 추이만

**추천 스코어링**: `total = w_dist·S_dist + w_skill·S_skill + w_time·S_time + w_host·S_host + w_fill·S_fill` (모두 [0,1])
- 기본 가중치 0.35 / 0.30 / 0.20 / 0.10 / 0.05. 거리↔실력 슬라이더가 `w_dist`·`w_skill`을 반비례 조정(합 0.65 유지)
- `S_dist = max(0, 1-(d/d_max)^1.5)` (기준점 여러 개면 최대값)
- `S_skill = exp(-(Δ)²/(2σ²))`, `σ = 150 + RD*0.5` (티어 범위 밖이면 0, 하드 필터 아님)
- `S_time`: 일치 1.0 / 인접 0.3 / 불일치 0. `S_host`: manner/5 × (1-노쇼율), 경기 3회 미만은 0.6. `S_fill`: 충족률 0.6~1.0이면 1.0, 아니면 0.5
- 하드 필터: 2시간 이내 시작, 성별 정책 불일치, 이미 지원/거절, 시간 겹침, 차단한 주최자
- 스코어링은 Python에서. 응답에 `score`·`breakdown`·`reasons`(추천 이유 칩)를 항상 포함 — **설명 가능성이 UX 핵심**

**거리 쿼리 (MariaDB)**: `ST_Distance_Sphere`만 쓰면 풀스캔 → **바운딩 박스(`MBRContains`) 선필터 후 정밀 거리 필터**, `cos(lat)` 보정, 후보 200개 상한.
`POINT(lng, lat)` 순서를 주석으로 명시. SPATIAL INDEX는 NOT NULL 컬럼만 가능.

**팀 분배**: 포지션 제약(풋살 팀당 GK 1) → rating 스네이크 드래프트 → 2-opt 스왑으로 합 차이 최소화. 주최자가 수동 조정 가능.

## 5. 보안 (최종 목표)
**방식**: v0 기능 완성 → 진단(Red: PoC 재현, `docs/security/findings/NNN-*.md`에 재현/영향/증거/심각도) → 방어(Blue: 패치 → 같은 PoC 재검증 → `tests/security/` 회귀 테스트).
공격 실습은 **우리 소유 로컬·스테이징에서만**. 공개 배포본에 의도적 취약점 금지(취약 버전은 `demo/vuln-*` 로컬 브랜치).
기본 방어(아래)는 W3부터 **모든 기능 PR에 포함**한다. W13~14는 진단·검증·문서화 주차.

**기본 코딩 규칙**
- SQL 문자열 조립 금지(f-string/`%`/`+`), 바인드 파라미터 100%
- 모든 엔드포인트에 인가 의존성(`Depends(require_*)`) + **객체 소유권 검사**. 없으면 머지 불가
- 응답은 Pydantic 화이트리스트 스키마만, ORM 객체·`dict` 직접 반환 금지
- 입력 검증은 Pydantic에서(길이·범위·enum), 좌표는 lat 33~39 / lng 124~132
- 인증: argon2, refresh 회전 + 재사용 감지, 로그아웃 시 무효화, JWT 알고리즘 화이트리스트
- 레이트리밋: 로그인 5/분, 매치 신청 10/분, 챗봇 20/5분, 지오코딩 30/시간
- 보안 헤더(HSTS, CSP, X-Content-Type-Options, Referrer-Policy, X-Frame-Options), 운영은 Swagger 비활성·CORS 제한
- 정원 초과 레이스는 `SELECT ... FOR UPDATE` / 유니크 제약으로 방지
- 스코어링·레이팅은 서버에서만 계산(클라이언트 입력은 필터 조건까지)
- 에러는 `{"detail": {"code": "MATCH_FULL", "message": "..."}}` 형태, 스택트레이스/SQL 노출 금지
- 로그에 토큰·비밀번호·좌표 마스킹, 로그인 실패·권한 거부는 보안 이벤트로 기록
- 시크릿은 `.env` + `Settings`만, 레포 커밋 금지(유출 시 즉시 폐기)
- 외부 URL 입력(지오코딩·이미지 등)은 스킴·호스트 화이트리스트, 내부망 IP 차단

**CI 게이트(PR)**: `bandit -r app -ll`, `ruff check --select S app`, `pip-audit`, `gitleaks detect`. ZAP은 리포트까지만.
**산출물**: 취약점 리포트 N건, STRIDE 위협 모델 1장, 라이브 데모 2~3개, 보안 체크리스트. 1인 1건 취약점 발표.

## 6. 챗봇 (`services/chatbot.py`, `POST /api/v1/chat` SSE)
역할은 4가지: ① 자연어 → `/matches/recommended` 파라미터 추출 ② 추천 결과 설명 ③ 온보딩 티어 안내 ④ 규칙 FAQ.
**순위는 6절 규칙 스코어링이 정하고, 챗봇은 정하지 않는다.**
- 도구는 **전부 읽기 전용**: `search_matches`(`user_id`는 서버가 JWT에서 주입), `get_my_profile`, `get_match_detail`, `suggest_action`(버튼 제안만)
- 도구는 항상 요청자 JWT 권한으로 실행. 소유권 검사는 서버가 한다
- `tool_choice`는 `auto` + 도구 `strict: true`(강제 `any`/`tool`은 400). 깊이는 `output_config.effort`(기본 `medium`), 파라미터 추출은 structured outputs
- 시스템 프롬프트·도구 정의는 프롬프트 캐싱, 요청마다 바뀌는 값은 캐시 분기점 뒤에
- 프롬프트 인젝션 대비: 도구 결과(공지·닉네임 등)는 데이터로만 취급·구분자로 감싸기, 챗봇 마크다운 렌더 시 HTML 비허용·링크는 자사 도메인만
- **PII는 도구 응답 스키마에서 애초에 제외**(좌표·주소·이메일·실명). 거리는 "약 2km"로 반올림해서만 전달
- 입력 길이·세션당 토큰 상한, `response.usage` 로깅, 인젝션 의심 입력은 보안 이벤트로 기록, 회귀 테스트는 `tests/security/test_chat_*.py`
- **LLM 장애 시 필터 UI로 degrade** — 챗봇 없이도 서비스가 완결돼야 한다. 대화 이력 30일 보관, 탈퇴 시 즉시 삭제

## 7. UX 원칙
피드 → 상세 → 신청 **3탭 유지**(챗봇 없이 측정), 추천 이유 항상 노출, 숫자 대신 시각 언어(티어 배지·접전도 게이지),
온보딩 3단계(종목 / 자기평가 / 활동 지역+거리), 웹 기본 + 반응형(데스크톱 상단 내비 / 모바일 하단 탭바), 홈(`/`)은 소개용 랜딩이고 활동은 `/dashboard`, 터치 타겟 44×44px 이상, 색만으로 상태 구분 금지, 폼 에러는 필드 옆 텍스트.

## 8. 개인정보
정확한 현재 위치 상시 수집 금지(등록한 기준점만). 타인에게는 거리를 "약 2km"로 반올림, 좌표·주소 원본 노출 금지.
탈퇴 시 개인정보 삭제·리뷰 익명화 보존. 더미 데이터에 실명·실주소 금지. 미성년자 가입 제외. 외부 LLM에 개인정보 전송 금지.

## 9. 개발 규칙
```bash
docker compose up -d
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
uv run pytest -q && uv run ruff check . && uv run ruff format . && uv run mypy app
cd frontend && pnpm install && pnpm dev && pnpm test && pnpm lint && pnpm typecheck
```
- 한국어 주석/커밋 허용, 식별자는 영어. Conventional Commits, 브랜치 `feat/<이슈번호>-<설명>`, `main` 직접 푸시 금지
- 마이그레이션은 `alembic revision --autogenerate` 후 **생성 파일을 반드시 검토**(공간 타입 오류 잦음)
- 환경변수는 `Settings`(pydantic-settings)로만, `os.environ` 직접 접근 금지
- async 코드에서 블로킹 I/O 금지(`httpx.AsyncClient`, `AsyncAnthropic`)
- 새 엔드포인트는 인가 의존성 + 보안 테스트 1개 필수
- 라우터 테스트는 happy path + 주요 에러만, 커버리지 목표 없음
- 알고리즘 가중치·공식 변경 시 같은 시드 데이터로 before/after 추천 결과를 PR에 기록

## 10. 일정 (14주)
W1 기획·ERD / W2 레포·docker·CI / W3 인증 / W4 구장·공간 쿼리 / W5 매치 CRUD·상태 전이 / **W6 추천** / **W7 레이팅** / **W8 밸런서** /
W9~11 프론트(온보딩·피드·상세·개설·매치룸·리뷰) / **W12 챗봇** / **W13 보안 진단(Red)** / **W14 보안 방어(Blue)·발표**.
**버리는 순서**: 지도 뷰 → 매치룸 채팅 → 알림 → 챗봇 온보딩·FAQ. 알고리즘 3종, 챗봇의 검색·설명, 보안은 끝까지 지킨다.
