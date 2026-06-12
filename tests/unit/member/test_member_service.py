import pytest
from sqlalchemy import text

from src.member.application.service.member_service import MemberService
from src.shared.domain.exception import EntityNotFoundException


@pytest.mark.asyncio
async def test_get_member_not_found(db_session):
    svc = MemberService(db_session)
    with pytest.raises(EntityNotFoundException):
        await svc.get_member("mem_x")


@pytest.mark.asyncio
async def test_get_ranking_group_filter(db_session):
    await db_session.execute(text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','조합1')"))
    await db_session.execute(text("INSERT INTO members(id, union_id, name, group_name, main_crop, region, created_at) VALUES ('mem_top','uni_001','A','TOP','한우','군위', NOW()),('mem_mid','uni_001','B','MIDDLE','한우','군위', NOW())"))
    await db_session.execute(text("INSERT INTO member_performances(member_id, union_id, period, rank, score, score_delta, production_score, shipping_score, revenue_score, production_weight, shipping_weight, revenue_weight, production_percentile, shipping_percentile, revenue_percentile) VALUES ('mem_top','uni_001','2026-05',1,90,1,30,30,30,35,35,30,90,90,90),('mem_mid','uni_001','2026-05',2,70,0,20,20,20,35,35,30,50,50,50)"))
    await db_session.commit()

    svc = MemberService(db_session)
    rows, total = await svc.get_ranking("uni_001", "2026-05", "TOP", 0, 20)
    assert total == 1
    assert rows[0][0].id == "mem_top"
