import logging
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.security_events import SecurityEvent, record_security_event
from app.core.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)

# teamup.* 로거(보안 이벤트, 챗봇 토큰 사용량)는 INFO부터 남긴다. 다른 라이브러리는 기본(WARNING) 그대로
logging.basicConfig(format="%(levelname)s %(name)s %(message)s")
logging.getLogger("teamup").setLevel(logging.INFO)

_SECURITY_STATUS: dict[int, SecurityEvent] = {
    401: "unauthorized",
    403: "forbidden",
    429: "rate_limited",
}


def _require_metrics_token(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> None:
    """METRICS_TOKEN이 있으면 Bearer 토큰이 맞아야 한다. 비어 있으면 local에서만 연다(스테이징·운영은 닫음)."""
    if not settings.metrics_token:
        if settings.env == "local":
            return
    else:
        scheme, _, given = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() == "bearer" and secrets.compare_digest(
            given.encode(), settings.metrics_token.encode()
        ):
            return
    raise HTTPException(
        status_code=401,
        detail={"code": "METRICS_UNAUTHORIZED", "message": "지표를 볼 권한이 없습니다"},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    docs_enabled = not settings.is_production  # 운영은 Swagger 비활성
    app = FastAPI(
        title=settings.app_name,
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(api_router)

    # Prometheus 수집용. 거부하면 401이고, 보안 이벤트(route="/metrics")로도 남는다
    @app.get("/metrics", include_in_schema=False, dependencies=[Depends(_require_metrics_token)])
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        # 401·403·429는 어디서 났든 여기서 한 번에 보안 이벤트로 남긴다
        if event := _SECURITY_STATUS.get(exc.status_code):
            detail: dict[str, object] = exc.detail if isinstance(exc.detail, dict) else {}
            route = getattr(request.scope.get("route"), "path", "")
            record_security_event(event, str(detail.get("code", exc.status_code)), route)
        return await http_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        # 스택트레이스·SQL은 로그에만 남기고 응답에는 노출하지 않는다
        logger.exception("unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": "INTERNAL_ERROR", "message": "서버 오류가 발생했습니다"}},
        )

    return app


app = create_app()
