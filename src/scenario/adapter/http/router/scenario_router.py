from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account_models import UserMemberLinkOrmModel
from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.ai.gemini_client import GeminiClient, GeminiUnavailableError
from src.infrastructure.database.session import get_db_session
from src.main.response_schema import CursorlessPageResponse, DataResponse
from src.scenario.adapter.persistence.model.scenario_model import ScenarioOrmModel
from src.shared.application.ids import new_id

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


class ScenarioChanges(BaseModel):
    fromCrop: str = Field(min_length=1, max_length=100)
    toCrop: str = Field(min_length=1, max_length=100)
    applyAreaRatio: float = Field(gt=0, le=1)
    startPeriod: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class ScenarioRequest(BaseModel):
    name: str = Field(default="시뮬레이션", min_length=1, max_length=150)
    memberId: str | None = None
    landId: str | None = None
    changes: ScenarioChanges

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_flat_request(cls, value: Any) -> Any:
        if isinstance(value, dict) and "changes" not in value:
            return {
                **value,
                "changes": {
                    "fromCrop": value.get("baseCrop"),
                    "toCrop": value.get("targetCrop"),
                    "applyAreaRatio": value.get("applyAreaRatio"),
                    "startPeriod": value.get("startPeriod"),
                },
            }
        return value

    @property
    def base_crop(self) -> str:
        return self.changes.fromCrop

    @property
    def target_crop(self) -> str:
        return self.changes.toCrop

    @property
    def apply_area_ratio(self) -> float:
        return self.changes.applyAreaRatio


class SaveScenarioRequest(BaseModel):
    scenarioId: str | None = None
    name: str = Field(min_length=1, max_length=150)
    memberId: str | None = None
    landId: str | None = None
    baseCrop: str | None = None
    targetCrop: str | None = None
    applyAreaRatio: float | None = Field(default=None, gt=0, le=1)


class ScenarioSimulationResult(BaseModel):
    scenarioId: str
    revenueChangePercent: float
    scoreChange: float
    riskLevel: Literal["LOW", "MEDIUM", "HIGH"]
    estimatedAnnualRevenueDelta: int
    aiAdvice: dict[str, object] | None
    aiModel: str


class SavedScenarioResult(BaseModel):
    scenarioId: str
    status: Literal["SAVED"]


class ScenarioListItem(BaseModel):
    scenarioId: str
    name: str
    memberId: str | None
    landId: str | None
    baseCrop: str
    targetCrop: str
    applyAreaRatio: float
    result: dict[str, object]
    createdAt: str


def calculate_simulation(body: ScenarioRequest) -> dict[str, object]:
    crop_factor = (sum(map(ord, body.target_crop)) % 21) - 10
    revenue_change = round((crop_factor * 1.7 + 8) * body.apply_area_ratio, 1)
    score_change = round((crop_factor * 0.4 + 4) * body.apply_area_ratio, 1)
    return {
        "revenueChangePercent": revenue_change,
        "scoreChange": score_change,
        "riskLevel": "LOW" if crop_factor >= 0 else "MEDIUM",
        "estimatedAnnualRevenueDelta": int(revenue_change * 100000),
    }


async def add_ai_explanation(
    body: ScenarioRequest,
    result: dict[str, object],
) -> dict[str, object]:
    client = GeminiClient()
    if not client.configured:
        return {**result, "aiAdvice": None, "aiModel": client.model}
    try:
        advice = await client.generate_json(
            system_instruction=(
                "당신은 한국 농업 작목 전환 전문 컨설턴트입니다. "
                "계산값을 변경하지 말고 현실적인 해설과 위험 요인을 한국어로 제공합니다."
            ),
            prompt=(
                f"기존 작목={body.base_crop}, 전환 작목={body.target_crop}, "
                f"전환 면적 비율={body.apply_area_ratio}, 계산 결과={result}. "
                'JSON만 반환: {"summary":"해설","actions":["실행 항목"],'
                '"riskFactors":["위험 요인"]}'
            ),
        )
        return {**result, "aiAdvice": advice, "aiModel": client.model}
    except GeminiUnavailableError:
        return {**result, "aiAdvice": None, "aiModel": client.model}


@router.post(
    "/simulate",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[ScenarioSimulationResult],
)
async def simulate_scenario(
    body: ScenarioRequest, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    result = await add_ai_explanation(body, calculate_simulation(body))
    row = ScenarioOrmModel(
        id=new_id("scn"),
        union_id=current.union_id,
        member_id=body.memberId,
        land_id=body.landId,
        name=body.name,
        base_crop=body.base_crop,
        target_crop=body.target_crop,
        apply_area_ratio=body.apply_area_ratio,
        result=result,
    )
    session.add(row)
    await session.commit()
    return ORJSONResponse({"data": {"scenarioId": row.id, **result}})


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=DataResponse[SavedScenarioResult]
)
async def save_scenario(
    body: SaveScenarioRequest, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    if body.scenarioId:
        row = await session.get(ScenarioOrmModel, body.scenarioId)
        if row is None or row.union_id != current.union_id:
            from src.shared.domain.exception import EntityNotFoundException

            raise EntityNotFoundException("Scenario", body.scenarioId)
        row.name = body.name
        await session.commit()
        return ORJSONResponse(
            status_code=201,
            content={"data": {"scenarioId": row.id, "status": "SAVED"}},
        )

    if not all((body.baseCrop, body.targetCrop, body.applyAreaRatio)):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail="scenarioId 또는 baseCrop, targetCrop, applyAreaRatio가 필요합니다.",
        )
    simulation = ScenarioRequest(
        name=body.name,
        memberId=body.memberId,
        landId=body.landId,
        changes=ScenarioChanges(
            fromCrop=body.baseCrop or "",
            toCrop=body.targetCrop or "",
            applyAreaRatio=body.applyAreaRatio or 0,
        ),
    )
    row = ScenarioOrmModel(
        id=new_id("scn"),
        union_id=current.union_id,
        member_id=body.memberId,
        land_id=body.landId,
        name=body.name,
        base_crop=simulation.base_crop,
        target_crop=simulation.target_crop,
        apply_area_ratio=simulation.apply_area_ratio,
        result=await add_ai_explanation(simulation, calculate_simulation(simulation)),
    )
    session.add(row)
    await session.commit()
    return ORJSONResponse(
        status_code=201, content={"data": {"scenarioId": row.id, "status": "SAVED"}}
    )


@router.get(
    "", status_code=status.HTTP_200_OK, response_model=CursorlessPageResponse[ScenarioListItem]
)
async def get_scenarios(
    current: CurrentUser,
    session: DbSession,
    memberId: str | None = None,
    size: int = Query(default=20, ge=1, le=100),
) -> ORJSONResponse:
    if memberId is None and current.role == "MEMBER":
        link = await session.get(UserMemberLinkOrmModel, current.user_id)
        memberId = link.member_id if link else None
    filters = [ScenarioOrmModel.union_id == current.union_id]
    if memberId:
        filters.append(ScenarioOrmModel.member_id == memberId)
    rows = list(
        (
            await session.scalars(
                select(ScenarioOrmModel)
                .where(*filters)
                .order_by(ScenarioOrmModel.created_at.desc())
                .limit(size)
            )
        ).all()
    )
    return ORJSONResponse(
        {
            "data": [
                {
                    "scenarioId": r.id,
                    "name": r.name,
                    "memberId": r.member_id,
                    "landId": r.land_id,
                    "baseCrop": r.base_crop,
                    "targetCrop": r.target_crop,
                    "applyAreaRatio": r.apply_area_ratio,
                    "result": r.result,
                    "createdAt": r.created_at.isoformat(),
                }
                for r in rows
            ],
            "page": 0,
            "size": size,
            "hasNext": len(rows) == size,
        }
    )


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: str, current: CurrentUser, session: DbSession
) -> Response:
    row = await session.get(ScenarioOrmModel, scenario_id)
    if row is None or row.union_id != current.union_id:
        from src.shared.domain.exception import EntityNotFoundException

        raise EntityNotFoundException("Scenario", scenario_id)
    await session.delete(row)
    await session.commit()
    return Response(status_code=204)
