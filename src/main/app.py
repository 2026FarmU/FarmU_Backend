from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel

from src.infrastructure.cache.redis import close_redis
from src.main.api_docs import configure_api_docs
from src.main.config import get_settings
from src.main.exception_handlers import register_exception_handlers

logger = structlog.get_logger()
settings = get_settings()


class HealthResponse(BaseModel):
    status: str
    version: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("FarmU API 시작", version=settings.app_version, env=settings.environment)
    yield
    await close_redis()
    logger.info("FarmU API 종료")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=None,
        redoc_url=None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 예외 핸들러
    register_exception_handlers(app)

    from src.shared.adapter.exception_handler import register_domain_exception_handlers

    register_domain_exception_handlers(app)

    # 헬스체크
    @app.get("/health", tags=["health"], response_model=HealthResponse)
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "version": settings.app_version}

    # BC 라우터 등록
    from src.auth.adapter.http.router.auth_router import router as auth_router
    from src.auth.adapter.http.router.user_router import router as user_router
    from src.data_ingest.adapter.http.router.data_router import router as data_router
    from src.infrastructure.ai.router import router as ai_router
    from src.land.adapter.http.router.land_router import router as land_router
    from src.member.adapter.http.router.member_router import router as member_router
    from src.member.adapter.http.router.search_router import router as search_router
    from src.mentoring.adapter.http.router.mentoring_router import router as mentoring_router
    from src.notification.adapter.http.router.notification_router import (
        router as notification_router,
    )
    from src.performance.adapter.http.router.dashboard_router import router as dashboard_router
    from src.report.adapter.http.router.report_router import router as report_router
    from src.scenario.adapter.http.router.scenario_router import router as scenario_router
    from src.shipping.adapter.http.router.shipping_router import router as shipping_router
    from src.union.adapter.http.router.weight_router import router as weight_router

    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(dashboard_router)
    app.include_router(member_router)
    app.include_router(shipping_router)
    app.include_router(notification_router)
    app.include_router(search_router)
    app.include_router(land_router)
    app.include_router(scenario_router)
    app.include_router(mentoring_router)
    app.include_router(report_router)
    app.include_router(data_router)
    app.include_router(weight_router)
    app.include_router(ai_router)

    configure_api_docs(app)

    return app


app = create_app()
