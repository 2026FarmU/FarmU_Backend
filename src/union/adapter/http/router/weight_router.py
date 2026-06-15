from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.account_models import UnionWeightOrmModel
from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.main.response_schema import DataResponse

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
router = APIRouter(prefix="/api/v1/settings/weights", tags=["settings"])


class WeightRequest(BaseModel):
    production: int = Field(ge=0, le=100)
    shipping: int = Field(ge=0, le=100)
    revenue: int = Field(ge=0, le=100)


class WeightResponse(WeightRequest):
    updatedAt: datetime


def serialize(row: UnionWeightOrmModel) -> dict[str, object]:
    return {
        "production": row.production,
        "shipping": row.shipping,
        "revenue": row.revenue,
        "updatedAt": row.updated_at,
    }


@router.get("", status_code=status.HTTP_200_OK, response_model=DataResponse[WeightResponse])
async def get_weights(current: CurrentUser, session: DbSession) -> ORJSONResponse:
    row = await session.get(UnionWeightOrmModel, current.union_id)
    if row is None:
        row = UnionWeightOrmModel(union_id=current.union_id)
        session.add(row)
        await session.commit()
    return ORJSONResponse({"data": serialize(row)})


@router.patch("", status_code=status.HTTP_200_OK, response_model=DataResponse[WeightResponse])
async def update_weights(
    body: WeightRequest, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    if current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="UNION_ADMIN 권한이 필요합니다.")
    if body.production + body.shipping + body.revenue != 100:
        raise HTTPException(status_code=400, detail="가중치 합계는 100이어야 합니다.")
    row = await session.get(UnionWeightOrmModel, current.union_id)
    if row is None:
        row = UnionWeightOrmModel(union_id=current.union_id)
        session.add(row)
    row.production = body.production
    row.shipping = body.shipping
    row.revenue = body.revenue
    row.updated_at = datetime.now(UTC)
    await session.commit()
    return ORJSONResponse({"data": serialize(row)})
