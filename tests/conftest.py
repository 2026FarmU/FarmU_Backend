import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://farmu:farmu@127.0.0.1:5434/farmu_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["DEBUG"] = "true"

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.auth.adapter.external.jwt_service_impl import JwtServiceImpl
from src.auth.application.port.required.jwt_service import TokenPayload
from src.infrastructure.database.session import Base
from src.main.app import create_app

from src.auth.adapter.persistence.model.union_model import UnionOrmModel  # noqa: F401
from src.auth.adapter.persistence.model.user_model import UserOrmModel  # noqa: F401
from src.member.adapter.persistence.model.member_model import (  # noqa: F401
    MemberImprovementTaskOrmModel,
    MemberOrmModel,
    MemberPerformanceOrmModel,
    MemberXaiFactorOrmModel,
)
from src.performance.adapter.persistence.model.dashboard_model import (  # noqa: F401
    UnionKpiOrmModel,
    UnionTrendOrmModel,
)
from src.alert.adapter.persistence.model.alert_model import AlertOrmModel  # noqa: F401
from src.shipping.adapter.persistence.model.shipping_model import (  # noqa: F401
    ShippingAccuracyOrmModel,
    ShippingRecommendationOrmModel,
)


@pytest.fixture()
async def db_session():
    engine = create_async_engine(os.environ["DATABASE_URL"], future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE shipping_accuracy_monthly, shipping_recommendations, alerts, union_trends, union_kpis, member_improvement_tasks, "
                "member_xai_factors, member_performances, members, users, unions "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture()
async def app_client(db_session):
    from src.auth.adapter.http.router import deps as auth_deps
    from src.member.adapter.http.router import member_router
    from src.performance.adapter.http.router import dashboard_router
    from src.shipping.adapter.http.router import shipping_router

    async def _override_session():
        yield db_session

    async def _override_current_payload(token: str = Depends(auth_deps._extract_bearer)):
        return JwtServiceImpl().decode_access_token(token)

    app = create_app()
    app.dependency_overrides[auth_deps.get_db_session] = _override_session
    app.dependency_overrides[member_router.get_db_session] = _override_session
    app.dependency_overrides[dashboard_router.get_db_session] = _override_session
    app.dependency_overrides[shipping_router.get_db_session] = _override_session
    app.dependency_overrides[auth_deps.get_current_token_payload] = _override_current_payload

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture()
def make_token():
    svc = JwtServiceImpl()

    def _make(user_id: str, role: str, union_id: str) -> str:
        token, _ = svc.create_access_token(TokenPayload(user_id=user_id, role=role, union_id=union_id))
        return token

    return _make
