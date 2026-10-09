# TeamUp (가칭)

거리·실력 기준으로 참가자를 매칭하는 팀 스포츠(농구·축구/풋살·배드민턴) 플랫폼. 상세 규칙은 [CLAUDE.md](CLAUDE.md).

## 시작하기
```bash
cp .env.example .env          # 값은 팀 채널에서 받기
cd frontend && pnpm install && pnpm dev
pnpm typecheck
```
백엔드(`backend/`)와 docker-compose는 W2에 추가 예정.

## 협업 규칙
- `main` 직접 푸시 금지. `feat/<이슈번호>-<설명>` 브랜치 → PR → 리뷰 1명 승인 후 머지
- 종목 담당자는 `frontend/src/sports/<종목>/` 안에서만 작업, 등록은 `registry.ts`
- 시크릿(`.env`, API 키)은 절대 커밋하지 않기
