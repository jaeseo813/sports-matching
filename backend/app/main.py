import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.security_events import SecurityEvent, record_security_event
from app.core.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)

_SECURITY_STATUS: dict[int, SecurityEvent] = {
    401: "unauthorized",
    403: "forbidden",
    429: "rate_limited",
}


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

    # Prometheus 수집용. 로컬·스테이징 전용이라 인증을 두지 않는다 (외부 공개 배포 금지)
    @app.get("/metrics", include_in_schema=False)
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
