import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_dashboard_summary_success(app_client, db_session, make_token):
    await db_session.execute(text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','조합1')"))
    await db_session.execute(text("INSERT INTO union_kpis(union_id, period, avg_score, score_delta, member_count, group_top, group_middle, group_needs_improvement, shipping_hit_rate, avg_revenue, report_time_reduced, last_updated) VALUES ('uni_001','2026-05',78.3,2.1,142,28,89,25,0.84,12500000,0.71, NOW())"))
    await db_session.commit()

    token = make_token("usr_1", "UNION_ADMIN", "uni_001")
    res = await app_client.get("/api/v1/dashboard/summary", params={"unionId": "uni_001", "period": "2026-05"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["avgScore"] == 78.3
    assert body["groupDistribution"]["top"] == 28


@pytest.mark.asyncio
async def test_dashboard_alerts_and_dismiss(app_client, db_session, make_token):
    await db_session.execute(text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','조합1')"))
    await db_session.execute(text("INSERT INTO alerts(id, union_id, level, status, type, title, message, affected_members, action_url, created_at) VALUES ('alt_1','uni_001','HIGH','ACTIVE','PRICE_DROP','t','m',12,'/x', NOW())"))
    await db_session.commit()

    token = make_token("usr_1", "UNION_ADMIN", "uni_001")
    res = await app_client.get("/api/v1/dashboard/alerts", params={"unionId": "uni_001", "status": "ACTIVE"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["totalElements"] == 1

    res2 = await app_client.patch("/api/v1/dashboard/alerts/alt_1", json={"status": "DISMISSED"}, headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 204


@pytest.mark.asyncio
async def test_dashboard_unauthorized(app_client):
    res = await app_client.get("/api/v1/dashboard/summary", params={"unionId": "uni_001", "period": "2026-05"})
    assert res.status_code == 401
