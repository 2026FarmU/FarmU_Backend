"""권한과 조합 범위를 적용한 전역 검색 API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.land.adapter.persistence.model.land_model import LandOrmModel
from src.main.response_schema import ListResponse
from src.member.adapter.persistence.model.member_model import MemberOrmModel
from src.report.adapter.persistence.model.report_model import ReportOrmModel

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

router = APIRouter(prefix="/api/v1/search", tags=["search"])


class SearchResult(BaseModel):
    type: str
    id: str
    title: str
    description: str
    actionUrl: str


@router.get("", status_code=status.HTTP_200_OK, response_model=ListResponse[SearchResult])
async def global_search(
    current: CurrentUser,
    session: DbSession,
    q: str = Query(min_length=2, max_length=100),
    size: int = Query(default=10, ge=1, le=20),
) -> ORJSONResponse:
    members = list(
        (
            await session.scalars(
                select(MemberOrmModel)
                .where(
                    MemberOrmModel.union_id == current.union_id,
                    MemberOrmModel.name.ilike(f"%{q}%"),
                )
                .order_by(MemberOrmModel.name)
                .limit(size)
            )
        ).all()
    )
    lands = list(
        (
            await session.scalars(
                select(LandOrmModel)
                .where(LandOrmModel.union_id == current.union_id, LandOrmModel.name.ilike(f"%{q}%"))
                .order_by(LandOrmModel.name)
                .limit(size)
            )
        ).all()
    )
    reports = list(
        (
            await session.scalars(
                select(ReportOrmModel)
                .where(
                    ReportOrmModel.union_id == current.union_id,
                    ReportOrmModel.period.ilike(f"%{q}%"),
                )
                .order_by(ReportOrmModel.created_at.desc())
                .limit(size)
            )
        ).all()
    )
    data = [
        {
            "type": "MEMBER",
            "id": row.id,
            "title": row.name,
            "description": f"{row.main_crop} · {row.region}",
            "actionUrl": f"/members/{row.id}",
        }
        for row in members
    ]
    data.extend(
        {
            "type": "LAND",
            "id": row.id,
            "title": row.name,
            "description": row.address,
            "actionUrl": f"/lands?landId={row.id}",
        }
        for row in lands
    )
    data.extend(
        {
            "type": "REPORT",
            "id": row.id,
            "title": f"{row.period} {row.report_type}",
            "description": row.status,
            "actionUrl": f"/reports?reportId={row.id}",
        }
        for row in reports
    )
    return ORJSONResponse({"data": data[:size]})
