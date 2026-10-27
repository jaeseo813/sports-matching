# 팀 작업 방식 안내

## 한 줄 요약
**디자인은 종목별로 자유롭게, 백엔드·DB는 하나를 같이 쓴다.**

## 왜 이렇게?
종목마다 백엔드와 DB를 따로 만들면 로그인·매치·추천 같은 똑같은 기능을 세 번 만들게 되고, 나중에 합칠 때 스키마가 어긋나서 크게 고생해요. 그래서 공통 기능은 하나로 만들고, 종목마다 다른 부분만 각자 맡아요.

## 역할
**1. 공통 코어 (같이 만듦, DB 하나)**
- 로그인/회원, 구장, 매치 개설·상태, 신청, 추천 점수, 실력(레이팅)
- 종목은 `sport` 컬럼으로 구분 (basketball / football / badminton)
- 주차별로 나눠서 담당을 정해요 (일정은 CLAUDE.md 10절 참고)

**2. 종목 모듈 (종목 담당자가 각자)**
- 프론트: `frontend/src/sports/<종목>/` 안의 화면과 디자인은 **마음대로** 해도 돼요.
- 백엔드: `backend/app/sports/<종목>/`에 이 종목만의 규칙을 적어요.
  - 팀 인원, 포지션(예: 풋살 골키퍼 1명), 티어 설명, 규칙 FAQ, 팀 밸런스 제약
- 자기 종목 폴더 안에서는 자유, 폴더 밖(공통 코어)을 바꿀 땐 PR로 올리고 리뷰를 받아요.

## 디자인 규칙
- 종목 페이지 안은 자유롭게!
- 색, 버튼, 카드, 티어 배지 같은 공통 요소는 `components/`에 있는 걸 가져다 써요. (통일감 유지)
- 중간(W10쯤)에 모여서 가장 괜찮은 디자인을 고르고, 나머지가 그 방향에 맞춰요.
- 피드 → 상세 → 신청 3탭 흐름은 유지해요.

## Git 규칙
1. `main`에 직접 푸시 금지 → 브랜치 `feat/<이슈번호>-<설명>` 만들어서 PR
2. PR 템플릿 체크리스트 확인 (보안 항목 포함)
3. `.env`, API 키는 절대 커밋 금지 (`.env.example`을 복사해서 사용)

## 백엔드 로컬 개발과 합치는 법
서버와 코드베이스는 하나입니다. 각자 자기 컴퓨터에서 같은 코드를 돌리고, **코드만 git으로 합칩니다.** (DB 데이터는 합치지 않아요)

**작업 흐름**
1. `main`을 pull하고 `feat/<이슈번호>-<설명>` 브랜치를 만들어요.
2. `docker compose up -d`로 내 컴퓨터에 DB·Redis를 띄워요. (DB는 각자 로컬 것)
3. `cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload`
4. 프론트는 `cd frontend && pnpm dev`로 띄워서 내 로컬 백엔드에 붙여요.
5. PR을 올리면 CI(lint, 테스트, 보안 스캔)가 돌고, 리뷰 1명 승인 후 머지해요.
6. 머지된 `main`을 pull한 사람은 `uv run alembic upgrade head`를 다시 실행해요.

**무엇이 합쳐지나**
- 코드: PR로 `main`에 머지
- DB 스키마: Alembic 마이그레이션 파일이 코드와 함께 git에 들어가요. `alembic upgrade head` 한 번이면 모두 같은 테이블 구조가 돼요.
- 테스트 데이터: 합치지 않아요. 공통으로 필요한 건 시드 스크립트로 만들어 각자 실행해요. (실명·실주소 금지)

**주의**
- **DB 스키마 변경은 코어 PR로 따로 올려요.** 종목 담당자는 가능하면 스키마를 건드리지 않고, 종목별 값은 `sport` 컬럼과 `backend/app/sports/<종목>/` 코드로 해결해요. 두 사람이 동시에 테이블을 바꾸면 Alembic head가 둘로 갈라져 충돌해요.
- 마이그레이션은 `alembic revision --autogenerate` 후 생성된 파일을 꼭 직접 검토해요. (공간 타입 오류가 잦아요)
- 브랜치를 오래 끌지 말고 작은 PR을 자주 올려요. 작업 전에 `main`을 rebase하거나 merge해요.
- 코어를 건드리는 PR은 리뷰 필수예요.

## 시작하기
```bash
git clone https://github.com/jaeseo813/sports-matching.git
cd sports-matching/frontend && pnpm install && pnpm dev
```
