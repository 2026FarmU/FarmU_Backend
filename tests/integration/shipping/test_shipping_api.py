import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_shipping_recommendations_and_decision(app_client, db_session, make_token):
    await db_session.execute(text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','조합1')"))
    await db_session.execute(text("INSERT INTO members(id, union_id, name, group_name, main_crop, region, created_at) VALUES ('mem_001','uni_001','홍길동','TOP','한우','군위', NOW())"))
    await db_session.execute(text("INSERT INTO shipping_recommendations(id, union_id, member_id, livestock_id, current_weight, target_weight, recommended_date, recommended_action, confidence, expected_revenue_min, expected_revenue_expected, expected_revenue_max, risk_type, risk_score, risk_note, rationale, status, created_at) VALUES ('shp_1','uni_001','mem_001','lvs_1',685.2,720,'2026-06-12','SHIP',0.87,8200000,8950000,9700000,'PRICE_VOLATILITY',0.32,'중간','근거','PENDING', NOW())"))
    await db_session.execute(text("INSERT INTO shipping_accuracy_monthly(union_id, period, total_recommendations, accepted, hit_rate) VALUES ('uni_001','2026-05',38,32,0.87)"))
    await db_session.commit()

    token = make_token('usr_1', 'UNION_ADMIN', 'uni_001')

    res1 = await app_client.get('/api/v1/shipping/recommendations', params={'unionId':'uni_001','status':'PENDING'}, headers={'Authorization':f'Bearer {token}'})
    assert res1.status_code == 200
    assert res1.json()['data'][0]['id'] == 'shp_1'

    res2 = await app_client.post('/api/v1/shipping/recommendations/shp_1/decision', json={'decision':'ACCEPTED','actualShipDate':'2026-06-12','memo':'ok'}, headers={'Authorization':f'Bearer {token}'})
    assert res2.status_code == 204

    res3 = await app_client.get('/api/v1/shipping/accuracy', params={'unionId':'uni_001','from':'2026-01','to':'2026-05'}, headers={'Authorization':f'Bearer {token}'})
    assert res3.status_code == 200
    assert res3.json()['data']['monthly'][0]['period'] == '2026-05'


@pytest.mark.asyncio
async def test_shipping_decision_conflict(app_client, db_session, make_token):
    await db_session.execute(text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','조합1')"))
    await db_session.execute(text("INSERT INTO members(id, union_id, name, group_name, main_crop, region, created_at) VALUES ('mem_001','uni_001','홍길동','TOP','한우','군위', NOW())"))
    await db_session.execute(text("INSERT INTO shipping_recommendations(id, union_id, member_id, livestock_id, current_weight, target_weight, recommended_date, recommended_action, confidence, expected_revenue_min, expected_revenue_expected, expected_revenue_max, risk_type, risk_score, risk_note, rationale, status, created_at) VALUES ('shp_1','uni_001','mem_001','lvs_1',685.2,720,'2026-06-12','SHIP',0.87,8200000,8950000,9700000,'PRICE_VOLATILITY',0.32,'중간','근거','ACCEPTED', NOW())"))
    await db_session.commit()

    token = make_token('usr_1', 'UNION_ADMIN', 'uni_001')
    res = await app_client.post('/api/v1/shipping/recommendations/shp_1/decision', json={'decision':'REJECTED'}, headers={'Authorization':f'Bearer {token}'})
    assert res.status_code == 409
