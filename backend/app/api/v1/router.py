from fastapi import APIRouter

from app.api.v1 import auth, health, matches, me, venues

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(venues.router)
api_router.include_router(matches.router)
api_router.include_router(me.router)
# 새 라우터는 여기에 include (각 엔드포인트에 인가 의존성 필수)
