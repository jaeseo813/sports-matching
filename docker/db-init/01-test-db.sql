-- 테스트 전용 DB. 개발 DB(teamup)의 데이터와 섞이지 않게 pytest는 여기만 쓴다.
-- 이 스크립트는 DB 볼륨을 처음 만들 때만 실행된다. 기존 볼륨이면 docs/progress.md의 명령으로 한 번 만든다.
CREATE DATABASE IF NOT EXISTS teamup_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON teamup_test.* TO 'teamup'@'%';
