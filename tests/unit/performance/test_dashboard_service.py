import pytest
from sqlalchemy import text

from src.performance.application.service.dashboard_service import DashboardService
from src.performance.domain.exception import PerformanceNotCalculatedException


@pytest.mark.asyncio
async def test_get_trends_not_found(db_session):
    svc = DashboardService(db_session)
    with pytest.raises(PerformanceNotCalculatedException):
        await svc.get_trends("uni_001", "2026-01", "2026-05", "score")


@pytest.mark.asyncio
async def test_dismiss_alert_invalid_status(db_session):
    await db_session.execute(text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','조합1')"))
    await db_session.execute(text("INSERT INTO alerts(id, union_id, level, status, type, title, message, affected_members, created_at) VALUES ('alt_1','uni_001','HIGH','ACTIVE','PRICE_DROP','t','m',1, NOW())"))
    await db_session.commit()

    svc = DashboardService(db_session)
    with pytest.raises(Exception):
        await svc.dismiss_alert("alt_1", "ACTIVE")
