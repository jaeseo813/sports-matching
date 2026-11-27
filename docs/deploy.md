# 배포 체크리스트

배포할 곳은 정해지지 않았다. 어디에 올리든 아래를 지킨다. 예시 값은 레포 루트 `.env.production.example`.

## 1. 설정 (서버 환경 변수)
| 변수 | 운영 값 | 틀리면 |
|---|---|---|
| `ENV` | `production` | 도커 이미지 기본값이 `production`이다. `local`이면 `/docs`와 토큰 없는 `/metrics`가 열린다 |
| `JWT_SECRET` | 32자 이상 무작위 (`openssl rand -hex 32`) | **서버가 시작되지 않는다** |
| `DATABASE_URL` | 운영 DB, 개발용과 다른 비밀번호 | 기본 비밀번호(`change-me`)면 **시작되지 않는다** |
| `CORS_ORIGINS` | 화면 주소만 | localhost가 있으면 **시작되지 않는다** |
| `DEEPSEEK_API_KEY` | 운영용 키 (사용량 한도 설정) | 비우면 챗봇만 꺼진다 |
| `METRICS_TOKEN` | 무작위 값 | 비우면 `/metrics`는 항상 401 (모니터링을 안 쓰면 비워도 된다) |
| `FORWARDED_ALLOW_IPS` | 앞단 프록시 주소 | 모든 사용자가 같은 IP로 보여 로그인 한도(5/분)를 다 같이 나눠 쓴다 |

화면은 빌드할 때 API 주소를 넣는다: `VITE_API_URL=https://<API 주소>/api/v1 pnpm build` → `frontend/dist`를 정적 호스팅.

## 2. 순서
1. 운영 DB를 만들고 `cd backend && uv run alembic upgrade head`
2. 관리자 지정: 가입 후 `uv run python -m scripts.make_admin <이메일>` → 내 정보에서 구장 등록 (구장이 없으면 매치를 열 수 없다)
3. API는 `backend/Dockerfile` 이미지로 띄운다. **워커·인스턴스는 1개**: 레이트리밋과 챗봇 토큰 상한이 서버 메모리에 있다
4. HTTPS는 앞단 프록시에서 건다 (토큰이 헤더로 오간다)

## 3. 하지 않는 것
- **`scripts.seed_dev`를 운영에서 돌리지 않는다** (`ENV=local`이 아니면 스스로 멈춘다)
- **운영 서버에 공격 실습을 하지 않는다** (AGENTS.md 5절). 실습은 로컬·스테이징에서
- `.env`·키를 레포에 올리지 않는다 (CI의 gitleaks가 막는다)

## 4. 알고 있는 한계
- 서버를 재시작하면 레이트리밋과 챗봇 토큰 사용량이 초기화된다
- 토큰은 브라우저 저장소에 있고 서버가 만료 전에 무효화할 수 없다(24시간). 탈퇴한 계정은 바로 막힌다
- 비밀번호 재설정(메일 발송) 기능은 없다
