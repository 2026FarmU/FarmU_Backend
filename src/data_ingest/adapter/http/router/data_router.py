import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import ORJSONResponse
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.http.router.deps import CurrentUser
from src.data_ingest.adapter.persistence.model.upload_model import DataUploadOrmModel
from src.infrastructure.database.session import get_db_session
from src.main.config import get_settings
from src.main.response_schema import DataResponse, PageResponse
from src.shared.application.ids import new_id
from src.shared.domain.exception import EntityNotFoundException

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
router = APIRouter(prefix="/api/v1/data", tags=["data"])
MAX_FILE_SIZE = 20 * 1024 * 1024
UPLOAD_DIR = Path("/tmp/farmu-uploads")  # noqa: S108


class CreateUploadRequest(BaseModel):
    fileName: str = Field(
        min_length=1,
        max_length=255,
        validation_alias=AliasChoices("fileName", "filename"),
    )
    dataType: Literal[
        "text/csv",
        "application/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ] = Field(validation_alias=AliasChoices("dataType", "contentType"))
    size: int = Field(gt=0, le=MAX_FILE_SIZE)


class UploadSessionResponse(BaseModel):
    uploadId: str
    uploadUrl: str
    method: Literal["PUT"]
    headers: dict[str, str]
    expiresAt: datetime
    status: Literal["PENDING_UPLOAD"]


class UploadMutationResponse(BaseModel):
    uploadId: str
    status: str


class ValidationErrorItem(BaseModel):
    row: int
    field: str | None = None
    value: object | None = None
    message: str


class UploadValidationResponse(BaseModel):
    uploadId: str
    status: str
    valid: bool
    totalRows: int
    errors: list[ValidationErrorItem]


class UploadHistoryItem(BaseModel):
    uploadId: str
    filename: str
    contentType: str
    size: int
    status: str
    valid: bool
    totalRows: int
    errorCount: int
    createdAt: datetime


class RowCorrectionRequest(BaseModel):
    values: dict[str, object]


def require_admin(current: CurrentUser) -> None:
    if current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="UNION_ADMIN 권한이 필요합니다.")


def sign_upload(upload_id: str, expires: int) -> str:
    return hmac.new(
        get_settings().jwt_secret_key.encode(),
        f"upload:{upload_id}:{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()


def validate_content(content: bytes) -> dict[str, object]:
    return {
        "valid": len(content) > 0,
        "totalRows": max(1, content.count(b"\n")),
        "errors": [] if content else [{"row": 0, "field": None, "message": "빈 파일입니다."}],
        "correctedRows": {},
    }


def validation_errors(validation: dict[str, object]) -> list[dict[str, object]]:
    value = validation.get("errors", [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def corrected_rows(validation: dict[str, object]) -> dict[str, object]:
    value = validation.get("correctedRows", {})
    return dict(value) if isinstance(value, dict) else {}


def validation_total_rows(validation: dict[str, object]) -> int:
    value = validation.get("totalRows", 0)
    return int(value) if isinstance(value, int | str) else 0


async def get_owned_upload(
    upload_id: str, current: CurrentUser, session: AsyncSession
) -> DataUploadOrmModel:
    require_admin(current)
    row = await session.get(DataUploadOrmModel, upload_id)
    if row is None or row.union_id != current.union_id:
        raise EntityNotFoundException("Upload", upload_id)
    return row


@router.post(
    "/uploads",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[UploadSessionResponse],
)
async def create_upload(
    body: CreateUploadRequest, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    require_admin(current)
    suffix = Path(body.fileName).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=415, detail="CSV 또는 XLSX 파일만 지원합니다.")
    upload_id = new_id("upl")
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    expires = int(expires_at.timestamp())
    signature = sign_upload(upload_id, expires)
    base = get_settings().public_base_url.rstrip("/")
    row = DataUploadOrmModel(
        id=upload_id,
        union_id=current.union_id,
        uploaded_by=current.user_id,
        filename=body.fileName,
        content_type=body.dataType,
        size=body.size,
        status="PENDING_UPLOAD",
        validation={"valid": False, "totalRows": 0, "errors": [], "correctedRows": {}},
    )
    session.add(row)
    await session.commit()
    return ORJSONResponse(
        status_code=201,
        content={
            "data": {
                "uploadId": upload_id,
                "uploadUrl": f"{base}/api/v1/data/uploads/{upload_id}/content?expires={expires}&signature={signature}",
                "method": "PUT",
                "headers": {"Content-Type": body.dataType},
                "expiresAt": expires_at.isoformat(),
                "status": "PENDING_UPLOAD",
            }
        },
    )


@router.put(
    "/uploads/{upload_id}/content",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[UploadMutationResponse],
)
async def put_upload_content(
    upload_id: str,
    expires: int,
    signature: str,
    request: Request,
    session: DbSession,
) -> ORJSONResponse:
    expected = sign_upload(upload_id, expires)
    if expires < int(datetime.now(UTC).timestamp()) or not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="업로드 URL이 만료되었거나 유효하지 않습니다.")
    row = await session.get(DataUploadOrmModel, upload_id)
    if row is None:
        raise EntityNotFoundException("Upload", upload_id)
    content = await request.body()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="파일은 최대 20MB입니다.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / upload_id).write_bytes(content)
    row.size = len(content)
    row.validation = validate_content(content)
    row.status = "VALIDATED" if row.validation["valid"] else "INVALID"
    await session.commit()
    return ORJSONResponse({"data": {"uploadId": row.id, "status": row.status}})


@router.post(
    "/uploads/direct",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[UploadMutationResponse],
)
async def upload_data_direct(
    current: CurrentUser, session: DbSession, file: UploadFile = File()
) -> ORJSONResponse:
    require_admin(current)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=415, detail="CSV 또는 XLSX 파일만 지원합니다.")
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="파일은 최대 20MB입니다.")
    validation = validate_content(content)
    row = DataUploadOrmModel(
        id=new_id("upl"),
        union_id=current.union_id,
        uploaded_by=current.user_id,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        status="VALIDATED" if validation["valid"] else "INVALID",
        validation=validation,
    )
    session.add(row)
    await session.commit()
    return ORJSONResponse(
        status_code=201, content={"data": {"uploadId": row.id, "status": row.status}}
    )


@router.get(
    "/uploads",
    status_code=status.HTTP_200_OK,
    response_model=PageResponse[UploadHistoryItem],
)
async def get_uploads(
    current: CurrentUser,
    session: DbSession,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
) -> ORJSONResponse:
    require_admin(current)
    filters = [DataUploadOrmModel.union_id == current.union_id]
    total = int(await session.scalar(select(func.count(DataUploadOrmModel.id)).where(*filters)) or 0)
    rows = list(
        (
            await session.scalars(
                select(DataUploadOrmModel)
                .where(*filters)
                .order_by(DataUploadOrmModel.created_at.desc())
                .offset(page * size)
                .limit(size)
            )
        ).all()
    )
    total_pages = 0 if total == 0 else (total + size - 1) // size
    return ORJSONResponse(
        {
            "data": [
                {
                    "uploadId": row.id,
                    "filename": row.filename,
                    "contentType": row.content_type,
                    "size": row.size,
                    "status": row.status,
                    "valid": bool(row.validation.get("valid", False)),
                    "totalRows": validation_total_rows(row.validation),
                    "errorCount": len(validation_errors(row.validation)),
                    "createdAt": row.created_at.isoformat(),
                }
                for row in rows
            ],
            "page": page,
            "size": size,
            "totalElements": total,
            "totalPages": total_pages,
            "hasNext": page + 1 < total_pages,
        }
    )


@router.get(
    "/uploads/{upload_id}/validation",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[UploadValidationResponse],
)
async def get_validation(
    upload_id: str, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    row = await get_owned_upload(upload_id, current, session)
    return ORJSONResponse({"data": {"uploadId": row.id, "status": row.status, **row.validation}})


@router.patch(
    "/uploads/{upload_id}/rows/{row_number}",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[UploadValidationResponse],
)
async def correct_upload_row(
    upload_id: str,
    row_number: int,
    body: RowCorrectionRequest,
    current: CurrentUser,
    session: DbSession,
) -> ORJSONResponse:
    row = await get_owned_upload(upload_id, current, session)
    validation = dict(row.validation)
    errors = [item for item in validation_errors(validation) if item.get("row") != row_number]
    corrected = corrected_rows(validation)
    corrected[str(row_number)] = body.values
    validation.update({"errors": errors, "correctedRows": corrected, "valid": len(errors) == 0})
    row.validation = validation
    row.status = "VALIDATED" if validation["valid"] else "INVALID"
    await session.commit()
    return ORJSONResponse({"data": {"uploadId": row.id, "status": row.status, **validation}})


@router.post(
    "/uploads/{upload_id}/revalidate",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[UploadValidationResponse],
)
async def revalidate_upload(
    upload_id: str, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    row = await get_owned_upload(upload_id, current, session)
    validation = dict(row.validation)
    validation["valid"] = len(validation_errors(validation)) == 0 and row.size > 0
    row.validation = validation
    row.status = "VALIDATED" if validation["valid"] else "INVALID"
    await session.commit()
    return ORJSONResponse({"data": {"uploadId": row.id, "status": row.status, **validation}})


async def commit_upload_impl(
    upload_id: str, current: CurrentUser, session: AsyncSession
) -> ORJSONResponse:
    row = await get_owned_upload(upload_id, current, session)
    if row.status != "VALIDATED":
        raise HTTPException(status_code=422, detail="검증에 성공한 파일만 반영할 수 있습니다.")
    row.status = "APPLIED"
    await session.commit()
    return ORJSONResponse({"data": {"uploadId": row.id, "status": row.status}})


@router.post(
    "/uploads/{upload_id}/commit",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[UploadMutationResponse],
)
async def commit_upload(
    upload_id: str, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    return await commit_upload_impl(upload_id, current, session)


@router.post(
    "/uploads/{upload_id}/apply",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[UploadMutationResponse],
    deprecated=True,
)
async def apply_upload(
    upload_id: str, current: CurrentUser, session: DbSession
) -> ORJSONResponse:
    return await commit_upload_impl(upload_id, current, session)
