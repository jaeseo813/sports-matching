from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
# 새 라우터는 여기에 include (각 엔드포인트에 인가 의존성 필수)
