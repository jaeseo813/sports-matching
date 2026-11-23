#!/usr/bin/env bash
# 보안 대시보드 라이브 데모: 공격 요청을 보내 Grafana 그래프가 바로 올라가는 걸 보여 준다.
# 로컬 API + 시드 데이터에서만 쓴다(더미 계정과 일부러 틀린 비밀번호만 사용).
# 받은 시드 계정 토큰은 ~/.cache/teamup-demo-token 에 둔다(24시간 유효, 데모 뒤 지워도 된다).
#
#   bash infra/monitoring/demo.sh prepare   # 발표 전에 한 번 (API를 띄운 뒤)
#   (1분 기다린 뒤)
#   bash infra/monitoring/demo.sh           # 발표 중
#
# prepare가 필요한 이유
# - Prometheus의 increase()는 새로 생긴 시계열의 첫 값을 증가로 세지 않는다.
#   API를 띄운 뒤 처음 나는 이벤트는 그래프에 안 보이므로, 종류별로 한 번씩 미리 발생시킨다.
# - 로그인은 IP당 1분 5회 제한이라, 본 실행에서 로그인 실패 5회를 다 쓰도록 토큰을 미리 받아 둔다.
set -euo pipefail

API=${API:-http://127.0.0.1:8000/api/v1}
EMAIL=${DEMO_EMAIL:-s1@seed.teamup.test}       # 시드 계정 (scripts/seed_dev.py)
PASSWORD=${DEMO_PASSWORD:-password123}         # 시드 계정 공용 더미 비밀번호
TOKEN_FILE=${DEMO_TOKEN_FILE:-$HOME/.cache/teamup-demo-token}  # 공유 /tmp를 피해 내 홈 아래에
GRAFANA=${GRAFANA_URL:-http://127.0.0.1:3000}
PY=$(command -v python3 || command -v python || true)
[ -n "$PY" ] || { echo "python3(또는 python)이 필요합니다." >&2; exit 1; }

status() { curl -s -o /dev/null -w "%{http_code}" "$@" || true; }

# JSON 응답에서 값 하나를 꺼낸다. API가 꺼졌거나 오류 응답이면 빈 문자열(스크립트를 죽이지 않는다).
json_pick() {
  "$PY" -c '
import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
if sys.argv[1] == "token":
    print(data.get("access_token", "") if isinstance(data, dict) else "")
elif isinstance(data, list):
    ids = [m["id"] for m in data if isinstance(m, dict) and not m.get("is_host", True)]
    print(ids[0] if ids else "")
' "$1"
}

bad_login() {
  status -X POST "$API/auth/login" -H 'content-type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"password\":\"wrong-password\"}"
}

# 요청자가 주최자가 아닌 매치 하나 (주최자 전용 동작을 시도해 403을 낸다)
pick_match() {
  { curl -s "$API/matches?limit=50" -H "authorization: Bearer $1" || true; } | json_pick match
}

forbidden() {
  status -X POST "$API/matches/$2/cancel" -H "authorization: Bearer $1"
}

# 챗봇에 너무 긴 입력(600자). 입력 가드가 규칙만으로 막아서 DeepSeek를 부르지 않는다(비용 없음).
# 서버에 DEEPSEEK_API_KEY가 없으면 가드 전에 503으로 끝난다.
too_long_chat() {
  long=$(printf '가%.0s' $(seq 600))
  status -X POST "$API/chat" -H "authorization: Bearer $1" -H 'content-type: application/json' \
    -d "{\"messages\":[{\"role\":\"user\",\"content\":\"$long\"}]}"
}

prepare() {
  echo "▶ 예열: 시드 계정으로 로그인해 토큰을 받아 둔다"
  token=$({ curl -s -X POST "$API/auth/login" -H 'content-type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" || true; } | json_pick token)
  if [ -z "$token" ]; then
    echo "로그인 실패. API가 떠 있는지, 시드 데이터가 있는지(uv run python -m scripts.seed_dev) 확인하세요." >&2
    exit 1
  fi
  mkdir -p "$(dirname "$TOKEN_FILE")"
  rm -f "$TOKEN_FILE"
  (umask 077 && printf '%s' "$token" >"$TOKEN_FILE")
  match=$(pick_match "$token")
  [ -n "$match" ] || { echo "주최자가 아닌 매치가 없습니다. 시드 데이터를 확인하세요." >&2; exit 1; }

  echo "▶ 예열: 이벤트 종류마다 한 번씩"
  echo "  401 토큰 없음      $(status "$API/auth/me")"
  echo "  403 남의 매치 취소 $(forbidden "$token" "$match")"
  chat=$(too_long_chat "$token")
  echo "  챗봇 너무 긴 입력  $chat$([ "$chat" = 503 ] && echo ' (챗봇 키 없음: 챗봇 단계는 건너뜀)')"
  printf "  401 로그인 실패 → 429 한도 초과:"
  for _ in 1 2 3 4 5; do printf " %s" "$(bad_login)"; done
  echo
  echo "완료. 로그인 한도가 풀리도록 1분 뒤에 'bash infra/monitoring/demo.sh'를 실행하세요."
}

run() {
  if [ ! -s "$TOKEN_FILE" ]; then
    echo "먼저 'bash infra/monitoring/demo.sh prepare'를 실행하세요." >&2
    exit 1
  fi
  token=$(cat "$TOKEN_FILE")
  match=$(pick_match "$token")
  [ -n "$match" ] || { echo "토큰이 만료됐거나 매치가 없습니다. prepare를 다시 실행하세요." >&2; exit 1; }

  echo "① 토큰 없이 내 정보 조회 10회 (unauthorized)"
  for _ in $(seq 10); do printf " %s" "$(status "$API/auth/me")"; done
  echo
  echo "② 틀린 비밀번호로 로그인 7회 (5회 INVALID_CREDENTIALS 뒤 rate_limited)"
  for _ in $(seq 7); do printf " %s" "$(bad_login)"; done
  echo
  echo "③ 남이 연 매치 취소 12회 (forbidden, 주최자 전용)"
  for _ in $(seq 12); do printf " %s" "$(forbidden "$token" "$match")"; done
  echo
  echo "④ 챗봇에 너무 긴 입력 3회 (chat_input_blocked TOO_LONG, 200 응답 안에 차단 메시지)"
  for _ in 1 2 3; do printf " %s" "$(too_long_chat "$token")"; done
  echo
  echo "대시보드: $GRAFANA/d/teamup-security  경보: http://127.0.0.1:9090/alerts"
}

case "${1:-run}" in
  prepare) prepare ;;
  run) run ;;
  *) echo "사용법: $0 [prepare|run]" >&2; exit 2 ;;
esac
