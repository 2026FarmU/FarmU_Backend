from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from src.main.config import get_settings
from src.main.exception_handlers import register_exception_handlers
from src.infrastructure.cache.redis import close_redis

logger = structlog.get_logger()
settings = get_settings()


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
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
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

    # 헬스체크
    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "version": settings.app_version}

    # TODO: 각 BC 라우터 등록
    # from src.auth.adapter.http.router import auth_router
    # app.include_router(auth_router, prefix="/api/v1")

    return app


app = create_app()
