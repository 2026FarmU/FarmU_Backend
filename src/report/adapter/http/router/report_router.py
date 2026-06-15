import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import ORJSONResponse
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.main.config import get_settings
from src.main.response_schema import CursorlessPageResponse, DataResponse
from src.report.adapter.persistence.model.report_model import ReportOrmModel
from src.shared.application.ids import new_id
from src.shared.domain.exception import EntityNotFoundException

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    type: Literal["MEMBER", "UNION", "MONTHLY"] = Field(
        default="MEMBER", validation_alias=AliasChoices("type", "reportType")
    )
    format: Literal["PDF", "CSV", "XLSX"] = "PDF"
    sections: list[str] = Field(default_factory=list)
    memberId: str | None = None
    unionId: str | None = None
    period: str


class ReportJobResponse(BaseModel):
    jobId: str
    status: Literal["COMPLETED"]
    estimatedSeconds: int
    pollingUrl: str


class ReportResponse(BaseModel):
    reportId: str
    memberId: str | None
    period: str
    type: str
    format: str
    sections: list[str]
    status: str
    downloadUrl: str
    downloadUrlExpiresAt: datetime
    createdAt: datetime


def serialize(row: ReportOrmModel) -> dict[str, object]:
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    expires = int(expires_at.timestamp())
    signature = hmac.new(
        get_settings().jwt_secret_key.encode(), f"{row.id}:{expires}".encode(), hashlib.sha256
    ).hexdigest()
    return {
        "reportId": row.id,
        "memberId": row.member_id,
        "period": row.period,
        "type": row.report_type,
        "format": row.format,
        "sections": row.sections,
        "status": row.status,
        "downloadUrl": f"/api/v1/reports/{row.id}/download?expires={expires}&signature={signature}",
        "downloadUrlExpiresAt": expires_at,
        "createdAt": row.created_at,
    }


@router.post(
    "/generate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DataResponse[ReportJobResponse],
)
async def generate_report(
    body: GenerateReportRequest, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    if body.unionId and body.unionId != current.union_id:
        raise HTTPException(status_code=403, detail="다른 조합의 리포트를 생성할 수 없습니다.")
    report_id = new_id("rpt")
    row = ReportOrmModel(
        id=report_id,
        union_id=current.union_id,
        member_id=body.memberId,
        period=body.period,
        report_type=body.type,
        format=body.format,
        sections=body.sections,
        status="READY",
        file_key=f"reports/{current.union_id}/{report_id}.pdf",
    )
    session.add(row)
    await session.commit()
    return ORJSONResponse(
        status_code=202,
        content={
            "data": {
                "jobId": report_id,
                "status": "COMPLETED",
                "estimatedSeconds": 0,
                "pollingUrl": f"/api/v1/reports/{report_id}",
            }
        },
    )


@router.get(
    "/{report_id}", status_code=status.HTTP_200_OK, response_model=DataResponse[ReportResponse]
)
async def get_report(report_id: str, current: CurrentUser, session: DbSession) -> ORJSONResponse:
    row = await session.get(ReportOrmModel, report_id)
    if row is None or row.union_id != current.union_id:
        raise EntityNotFoundException("Report", report_id)
    return ORJSONResponse({"data": serialize(row)})


@router.get(
    "/{report_id}/download",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def download_report(
    report_id: str, expires: int, signature: str, session: DbSession
) -> Response:
    expected = hmac.new(
        get_settings().jwt_secret_key.encode(), f"{report_id}:{expires}".encode(), hashlib.sha256
    ).hexdigest()
    if expires < int(datetime.now(UTC).timestamp()) or not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=403, detail="다운로드 URL이 만료되었거나 유효하지 않습니다."
        )
    row = await session.get(ReportOrmModel, report_id)
    if row is None:
        raise EntityNotFoundException("Report", report_id)
    content = (
        f"FarmU Report\nReport: {row.id}\nPeriod: {row.period}\nType: {row.report_type}\n".encode()
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{row.id}.pdf"'},
    )


@router.get(
    "", status_code=status.HTTP_200_OK, response_model=CursorlessPageResponse[ReportResponse]
)
async def get_reports(
    current: CurrentUser,
    session: DbSession,
    period: str | None = None,
    page: int = 0,
    size: int = Query(default=20, ge=1, le=100),
) -> ORJSONResponse:
    filters = [ReportOrmModel.union_id == current.union_id]
    if period:
        filters.append(ReportOrmModel.period == period)
    rows = list(
        (
            await session.scalars(
                select(ReportOrmModel)
                .where(*filters)
                .order_by(ReportOrmModel.created_at.desc())
                .offset(page * size)
                .limit(size)
            )
        ).all()
    )
    return ORJSONResponse(
        {
            "data": [serialize(r) for r in rows],
            "page": page,
            "size": size,
            "hasNext": len(rows) == size,
        }
    )
