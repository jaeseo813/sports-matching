#!/usr/bin/env bash
# 보안 대시보드 라이브 데모: 공격 요청을 보내 Grafana 그래프가 바로 올라가는 걸 보여 준다.
# 로컬 API + 시드 데이터에서만 쓴다(더미 계정과 일부러 틀린 비밀번호만 사용).
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
TOKEN_FILE=${TMPDIR:-/tmp}/teamup-demo-token

status() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

bad_login() {
  status -X POST "$API/auth/login" -H 'content-type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"password\":\"wrong-password\"}"
}

# 요청자가 주최자가 아닌 매치 하나 (주최자 전용 동작을 시도해 403을 낸다)
pick_match() {
  curl -s "$API/matches?limit=50" -H "authorization: Bearer $1" | python3 -c '
import json, sys
ids = [m["id"] for m in json.load(sys.stdin) if not m["is_host"]]
print(ids[0] if ids else "")'
}

forbidden() {
  status -X POST "$API/matches/$2/cancel" -H "authorization: Bearer $1"
}

prepare() {
  echo "▶ 예열: 시드 계정으로 로그인해 토큰을 받아 둔다"
  token=$(curl -s -X POST "$API/auth/login" -H 'content-type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))')
  if [ -z "$token" ]; then
    echo "로그인 실패. API가 떠 있는지, 시드 데이터가 있는지(uv run python -m scripts.seed_dev) 확인하세요." >&2
    exit 1
  fi
  (umask 077 && printf '%s' "$token" >"$TOKEN_FILE")
  match=$(pick_match "$token")
  [ -n "$match" ] || { echo "주최자가 아닌 매치가 없습니다. 시드 데이터를 확인하세요." >&2; exit 1; }

  echo "▶ 예열: 이벤트 종류마다 한 번씩"
  echo "  401 토큰 없음      $(status "$API/auth/me")"
  echo "  403 남의 매치 취소 $(forbidden "$token" "$match")"
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
  echo "대시보드: http://127.0.0.1:3000/d/teamup-security  경보: http://127.0.0.1:9090/alerts"
}

case "${1:-run}" in
  prepare) prepare ;;
  run) run ;;
  *) echo "사용법: $0 [prepare|run]" >&2; exit 2 ;;
esac
