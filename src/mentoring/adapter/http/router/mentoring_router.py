from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.main.response_schema import DataResponse, ListResponse
from src.member.adapter.persistence.model.member_model import (
    MemberOrmModel,
    MemberPerformanceOrmModel,
)
from src.mentoring.adapter.persistence.model.mentoring_model import (
    MentoringMatchOrmModel,
    MentoringTaskOrmModel,
)
from src.shared.application.ids import new_id
from src.shared.domain.exception import EntityNotFoundException

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
router = APIRouter(prefix="/api/v1/mentoring", tags=["mentoring"])

HelpArea = Literal["PRODUCTION", "SHIPPING", "REVENUE", "QUALITY", "COST", "CROP_CHANGE", "CONNECT"]


class MatchRequest(BaseModel):
    menteeId: str
    mentorId: str
    goal: str | None = Field(default=None, min_length=1, max_length=1000)
    helpAreas: list[HelpArea] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_goal_or_help_area(self) -> "MatchRequest":
        if not self.goal and not self.helpAreas:
            raise ValueError("goal 또는 helpAreas가 필요합니다.")
        return self


class MentorSuggestion(BaseModel):
    mentorId: str
    name: str
    mainCrop: str
    region: str
    score: int
    matchScore: int
    helpAreas: list[str]
    matchReasons: list[str]
    distanceKm: float


class MatchFactor(BaseModel):
    factor: str
    score: float


class MentorComparison(BaseModel):
    category: str
    menteeScore: float
    mentorScore: float


class MentorHelpArea(BaseModel):
    category: str
    title: str
    description: str


class MentorDetailResponse(BaseModel):
    mentorId: str
    name: str
    mainCrop: str
    region: str
    score: int
    matchScore: int
    years: int
    distanceKm: float
    reason: str
    tags: list[str]
    matchFactors: list[MatchFactor]
    comparison: list[MentorComparison]
    helpAreas: list[MentorHelpArea]


class MatchResponse(BaseModel):
    matchId: str
    status: str


class MentoringTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    dueDate: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    completed: bool = False


class MentoringTaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    dueDate: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    completed: bool | None = None


class MentoringTaskResponse(BaseModel):
    taskId: str
    matchId: str
    title: str
    description: str | None
    dueDate: str | None
    completed: bool
    createdAt: str


def serialize_task(row: MentoringTaskOrmModel) -> dict[str, object]:
    return {
        "taskId": row.id,
        "matchId": row.match_id,
        "title": row.title,
        "description": row.description,
        "dueDate": row.due_date,
        "completed": row.completed,
        "createdAt": row.created_at.isoformat(),
    }


def estimated_distance_km(region_a: str, region_b: str) -> float:
    return 0.0 if region_a == region_b else round(10 + sum(map(ord, region_a + region_b)) % 900 / 10, 1)


def help_area_details(perf: MemberPerformanceOrmModel) -> list[dict[str, str]]:
    scores = [
        ("PRODUCTION", "생산 관리", "생산성 향상과 재배 운영 노하우", float(perf.production_score)),
        ("SHIPPING", "출하 전략", "적정 출하시점과 출하 의사결정", float(perf.shipping_score)),
        ("REVENUE", "수익 개선", "비용 대비 수익성과 판매 전략", float(perf.revenue_score)),
    ]
    return [
        {"category": category, "title": title, "description": description}
        for category, title, description, _score in sorted(scores, key=lambda item: item[3], reverse=True)
    ][:2]


async def get_owned_match(
    match_id: str, current: CurrentUser, session: AsyncSession
) -> MentoringMatchOrmModel:
    row = await session.get(MentoringMatchOrmModel, match_id)
    if row is None or row.union_id != current.union_id:
        raise EntityNotFoundException("Match", match_id)
    return row


@router.get(
    "/suggestions",
    status_code=status.HTTP_200_OK,
    response_model=ListResponse[MentorSuggestion],
)
async def get_suggestions(
    current: CurrentUser,
    session: DbSession,
    menteeId: str,
    size: int = Query(default=5, ge=1, le=20),
) -> ORJSONResponse:
    mentee = await session.get(MemberOrmModel, menteeId)
    if mentee is None or mentee.union_id != current.union_id:
        raise EntityNotFoundException("Member", menteeId)
    rows = (
        await session.execute(
            select(MemberOrmModel, MemberPerformanceOrmModel)
            .where(
                MemberOrmModel.id == MemberPerformanceOrmModel.member_id,
                MemberOrmModel.union_id == current.union_id,
                MemberOrmModel.id != menteeId,
            )
            .order_by(MemberPerformanceOrmModel.score.desc())
            .limit(size)
        )
    ).all()
    return ORJSONResponse(
        {
            "data": [
                {
                    "mentorId": member.id,
                    "name": member.name,
                    "mainCrop": member.main_crop,
                    "region": member.region,
                    "score": round(float(perf.score)),
                    "matchScore": max(50, min(100, round(float(perf.score)))),
                    "helpAreas": ["PRODUCTION", "SHIPPING"],
                    "matchReasons": [
                        f"{member.main_crop} 재배 경험",
                        f"조합 성과 {round(float(perf.score))}점",
                    ],
                    "distanceKm": estimated_distance_km(mentee.region, member.region),
                }
                for member, perf in rows
            ]
        }
    )


@router.get(
    "/suggestions/{mentor_id}",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[MentorDetailResponse],
)
async def get_suggestion_detail(
    mentor_id: str,
    current: CurrentUser,
    session: DbSession,
    menteeId: str | None = None,
) -> ORJSONResponse:
    row = (
        await session.execute(
            select(MemberOrmModel, MemberPerformanceOrmModel)
            .where(
                MemberOrmModel.id == mentor_id,
                MemberOrmModel.union_id == current.union_id,
                MemberPerformanceOrmModel.member_id == MemberOrmModel.id,
            )
            .order_by(MemberPerformanceOrmModel.period.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        raise EntityNotFoundException("Mentor", mentor_id)
    member, perf = row
    score = round(float(perf.score))
    mentee = await session.get(MemberOrmModel, menteeId) if menteeId else None
    mentee_perf = None
    if mentee is not None and mentee.union_id == current.union_id:
        mentee_perf = await session.scalar(
            select(MemberPerformanceOrmModel)
            .where(MemberPerformanceOrmModel.member_id == mentee.id)
            .order_by(MemberPerformanceOrmModel.period.desc())
            .limit(1)
        )
    distance = estimated_distance_km(mentee.region, member.region) if mentee else 0.0
    comparisons = []
    if mentee_perf is not None:
        comparisons = [
            {"category": "PRODUCTION", "menteeScore": float(mentee_perf.production_score), "mentorScore": float(perf.production_score)},
            {"category": "SHIPPING", "menteeScore": float(mentee_perf.shipping_score), "mentorScore": float(perf.shipping_score)},
            {"category": "REVENUE", "menteeScore": float(mentee_perf.revenue_score), "mentorScore": float(perf.revenue_score)},
        ]
    help_areas = help_area_details(perf)
    return ORJSONResponse(
        {
            "data": {
                "mentorId": member.id,
                "name": member.name,
                "mainCrop": member.main_crop,
                "region": member.region,
                "score": score,
                "matchScore": max(50, min(100, score)),
                "years": max(1, datetime.now(UTC).year - member.created_at.year + 1),
                "distanceKm": distance,
                "reason": f"{member.main_crop} 분야의 성과와 경험이 멘티의 개선 목표에 적합합니다.",
                "tags": [member.main_crop, member.region, "고성과 멘토"],
                "matchFactors": [
                    {"factor": "PERFORMANCE", "score": float(perf.score)},
                    {"factor": "CROP_MATCH", "score": 100.0 if mentee and mentee.main_crop == member.main_crop else 70.0},
                    {"factor": "DISTANCE", "score": max(0.0, 100.0 - distance)},
                ],
                "comparison": comparisons,
                "helpAreas": help_areas,
            }
        }
    )


@router.post(
    "/matches", status_code=status.HTTP_201_CREATED, response_model=DataResponse[MatchResponse]
)
async def create_match(
    body: MatchRequest, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    if body.menteeId == body.mentorId:
        raise HTTPException(status_code=400, detail="본인을 멘토로 지정할 수 없습니다.")
    members = list(
        (
            await session.scalars(
                select(MemberOrmModel).where(
                    MemberOrmModel.id.in_([body.menteeId, body.mentorId]),
                    MemberOrmModel.union_id == current.union_id,
                )
            )
        ).all()
    )
    if len(members) != 2:
        raise EntityNotFoundException("Member", body.mentorId)
    row = MentoringMatchOrmModel(
        id=new_id("mtc"),
        union_id=current.union_id,
        mentee_id=body.menteeId,
        mentor_id=body.mentorId,
        help_areas=body.helpAreas or ["CONNECT"],
        goal=body.goal,
        status="PENDING",
    )
    session.add(row)
    await session.commit()
    return ORJSONResponse(
        status_code=201, content={"data": {"matchId": row.id, "status": row.status}}
    )


@router.patch(
    "/matches/{match_id}/approve",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[MatchResponse],
)
async def approve_match(match_id: str, current: CurrentUser, session: DbSession) -> ORJSONResponse:
    if current.role not in ("UNION_ADMIN", "CONSULTANT"):
        raise HTTPException(status_code=403, detail="승인 권한이 없습니다.")
    row = await session.get(MentoringMatchOrmModel, match_id)
    if row is None or row.union_id != current.union_id:
        raise EntityNotFoundException("Match", match_id)
    if row.status != "PENDING":
        raise HTTPException(status_code=409, detail="승인할 수 없는 상태입니다.")
    row.status = "APPROVED"
    await session.commit()
    return ORJSONResponse({"data": {"matchId": row.id, "status": row.status}})


@router.patch(
    "/matches/{match_id}/reject",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[MatchResponse],
)
async def reject_match(match_id: str, current: CurrentUser, session: DbSession) -> ORJSONResponse:
    row = await get_owned_match(match_id, current, session)
    if row.status != "PENDING":
        raise HTTPException(status_code=409, detail="거절할 수 없는 상태입니다.")
    row.status = "REJECTED"
    await session.commit()
    return ORJSONResponse({"data": {"matchId": row.id, "status": row.status}})


@router.get(
    "/matches/{match_id}/tasks",
    status_code=status.HTTP_200_OK,
    response_model=ListResponse[MentoringTaskResponse],
)
async def get_tasks(match_id: str, current: CurrentUser, session: DbSession) -> ORJSONResponse:
    await get_owned_match(match_id, current, session)
    rows = list(
        (
            await session.scalars(
                select(MentoringTaskOrmModel)
                .where(MentoringTaskOrmModel.match_id == match_id)
                .order_by(MentoringTaskOrmModel.created_at)
            )
        ).all()
    )
    return ORJSONResponse({"data": [serialize_task(row) for row in rows]})


@router.post(
    "/matches/{match_id}/tasks",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[MentoringTaskResponse],
)
async def create_task(
    match_id: str,
    body: MentoringTaskRequest,
    current: CurrentUser,
    session: DbSession,
) -> ORJSONResponse:
    match = await get_owned_match(match_id, current, session)
    if match.status != "APPROVED":
        raise HTTPException(status_code=409, detail="승인된 매칭에만 과제를 추가할 수 있습니다.")
    row = MentoringTaskOrmModel(
        id=new_id("tsk"),
        match_id=match_id,
        title=body.title,
        description=body.description,
        due_date=body.dueDate,
        completed=body.completed,
    )
    session.add(row)
    await session.commit()
    return ORJSONResponse(status_code=201, content={"data": serialize_task(row)})


@router.patch(
    "/matches/{match_id}/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[MentoringTaskResponse],
)
async def update_task(
    match_id: str,
    task_id: str,
    body: MentoringTaskPatch,
    current: CurrentUser,
    session: DbSession,
) -> ORJSONResponse:
    await get_owned_match(match_id, current, session)
    row = await session.get(MentoringTaskOrmModel, task_id)
    if row is None or row.match_id != match_id:
        raise EntityNotFoundException("MentoringTask", task_id)
    values = body.model_dump(exclude_unset=True)
    if "title" in values:
        row.title = values["title"]
    if "description" in values:
        row.description = values["description"]
    if "dueDate" in values:
        row.due_date = values["dueDate"]
    if "completed" in values:
        row.completed = values["completed"]
    await session.commit()
    return ORJSONResponse({"data": serialize_task(row)})
