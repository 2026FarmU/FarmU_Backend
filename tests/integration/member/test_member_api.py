import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_member_ranking_and_analysis(app_client, db_session, make_token):
    await db_session.execute(text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','조합1')"))
    await db_session.execute(text("INSERT INTO members(id, union_id, name, group_name, main_crop, region, created_at) VALUES ('mem_001','uni_001','김상위','TOP','한우','군위', NOW())"))
    await db_session.execute(text("INSERT INTO member_performances(member_id, union_id, period, rank, score, score_delta, production_score, shipping_score, revenue_score, production_weight, shipping_weight, revenue_weight, production_percentile, shipping_percentile, revenue_percentile) VALUES ('mem_001','uni_001','2026-05',1,92.4,1.2,33.1,31.8,27.5,35,35,30,95,92,90)"))
    await db_session.execute(text("INSERT INTO member_xai_factors(member_id, period, factor, contribution, direction, description) VALUES ('mem_001','2026-05','출하시점지연',-8.4,'negative','권고일보다 지연')"))
    await db_session.execute(text("INSERT INTO member_improvement_tasks(id, member_id, period, priority, title, category, expected_score_delta, expected_revenue_delta) VALUES ('tsk_01','mem_001','2026-05',1,'출하 시점 단축','SHIPPING',6.5,1800000)"))
    await db_session.commit()

    token = make_token("usr_1", "UNION_ADMIN", "uni_001")
    r1 = await app_client.get("/api/v1/members/ranking", params={"unionId":"uni_001","period":"2026-05"}, headers={"Authorization":f"Bearer {token}"})
    assert r1.status_code == 200
    assert r1.json()["data"][0]["memberId"] == "mem_001"

    r2 = await app_client.get("/api/v1/members/mem_001/analysis", params={"period":"2026-05"}, headers={"Authorization":f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["data"]["totalScore"] == 92.4


@pytest.mark.asyncio
async def test_member_analysis_not_found(app_client, db_session, make_token):
    await db_session.execute(text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','조합1')"))
    await db_session.commit()
    token = make_token("usr_1", "UNION_ADMIN", "uni_001")
    r = await app_client.get("/api/v1/members/mem_x/analysis", params={"period":"2026-05"}, headers={"Authorization":f"Bearer {token}"})
    assert r.status_code == 404
