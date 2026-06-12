import pytest
from sqlalchemy import text

from src.shipping.application.service.shipping_service import ShippingService
from src.shipping.domain.exception import RecommendationAlreadyDecidedException


@pytest.mark.asyncio
async def test_decision_conflict(db_session):
    await db_session.execute(text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','조합1')"))
    await db_session.execute(text("INSERT INTO members(id, union_id, name, group_name, main_crop, region, created_at) VALUES ('mem_001','uni_001','홍길동','TOP','한우','군위', NOW())"))
    await db_session.execute(text("INSERT INTO shipping_recommendations(id, union_id, member_id, livestock_id, current_weight, target_weight, recommended_date, recommended_action, confidence, expected_revenue_min, expected_revenue_expected, expected_revenue_max, risk_type, risk_score, risk_note, rationale, status, created_at) VALUES ('shp_1','uni_001','mem_001','lvs_1',685.2,720,'2026-06-12','SHIP',0.87,8200000,8950000,9700000,'PRICE_VOLATILITY',0.32,'중간','근거','ACCEPTED', NOW())"))
    await db_session.commit()

    svc = ShippingService(db_session)
    with pytest.raises(RecommendationAlreadyDecidedException):
        await svc.decide_recommendation('shp_1', 'REJECTED', None, None)
