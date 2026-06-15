from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account_models import UserMemberLinkOrmModel
from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.land.adapter.persistence.model.land_model import LandOrmModel, LandSuitabilityOrmModel
from src.main.response_schema import CursorlessPageResponse, DataResponse
from src.shared.domain.exception import EntityNotFoundException

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
router = APIRouter(prefix="/api/v1/lands", tags=["lands"])


class LandItem(BaseModel):
    landId: str
    memberId: str
    name: str
    pnu: str
    address: str
    latitude: float
    longitude: float
    area: float
    mainCrop: str


class SuitabilityCandidate(BaseModel):
    crop: str
    score: float
    reasons: list[str]


class LandSuitabilityResponse(BaseModel):
    landId: str
    currentCrop: str
    candidates: list[SuitabilityCandidate]


@router.get(
    "", status_code=status.HTTP_200_OK, response_model=CursorlessPageResponse[LandItem]
)
async def get_lands(
    current: CurrentUser,
    session: DbSession,
    memberId: str | None = None,
    page: int = 0,
    size: int = Query(default=20, ge=1, le=100),
) -> ORJSONResponse:
    if memberId is None and current.role == "MEMBER":
        link = await session.get(UserMemberLinkOrmModel, current.user_id)
        memberId = link.member_id if link else None
    filters = [LandOrmModel.union_id == current.union_id]
    if memberId:
        filters.append(LandOrmModel.member_id == memberId)
    rows = list(
        (
            await session.scalars(
                select(LandOrmModel)
                .where(*filters)
                .order_by(LandOrmModel.created_at.desc())
                .offset(page * size)
                .limit(size)
            )
        ).all()
    )
    return ORJSONResponse(
        {
            "data": [
                {
                    "landId": r.id,
                    "memberId": r.member_id,
                    "name": r.name,
                    "pnu": r.pnu,
                    "address": r.address,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "area": float(r.area),
                    "mainCrop": r.main_crop,
                }
                for r in rows
            ],
            "page": page,
            "size": size,
            "hasNext": len(rows) == size,
        }
    )


@router.get(
    "/{land_id}/suitability",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[LandSuitabilityResponse],
)
async def get_suitability(land_id: str, current: CurrentUser, session: DbSession) -> ORJSONResponse:
    land = await session.get(LandOrmModel, land_id)
    if land is None or land.union_id != current.union_id:
        raise EntityNotFoundException("Land", land_id)
    rows = list(
        (
            await session.scalars(
                select(LandSuitabilityOrmModel)
                .where(LandSuitabilityOrmModel.land_id == land_id)
                .order_by(LandSuitabilityOrmModel.score.desc())
            )
        ).all()
    )
    return ORJSONResponse(
        {
            "data": {
                "landId": land.id,
                "currentCrop": land.main_crop,
                "candidates": [
                    {"crop": r.crop, "score": r.score, "reasons": r.reasons} for r in rows
                ],
            }
        }
    )
