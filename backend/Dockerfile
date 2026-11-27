FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN useradd --create-home appuser
USER appuser
ENV PATH="/app/.venv/bin:$PATH"
# ENV를 빠뜨려도 개발 모드로 뜨지 않게 이미지 기본은 운영 (로컬 compose는 .env의 ENV=local이 덮어쓴다)
ENV ENV=production
# 프록시 뒤에서 실제 접속 IP를 읽는다 (레이트리밋이 IP로 센다). 프록시 주소는 FORWARDED_ALLOW_IPS로 준다
# 워커는 1개: 레이트리밋·챗봇 토큰 상한이 메모리에 있다 (docs/deploy.md)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
