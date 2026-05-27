"""도메인 예외 → HTTP 응답 매핑 미들웨어."""
from datetime import UTC, datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse

from src.shared.domain.exception import (
    BusinessRuleViolationException,
    ConflictException,
    DomainException,
    EntityNotFoundException,
    InsufficientDataException,
)


def _problem(status_code: int, detail: str, path: str, code: str) -> dict:
    titles = {
        400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
        404: "Not Found", 409: "Conflict", 422: "Unprocessable Entity",
        500: "Internal Server Error",
    }
    return {
        "type": "about:blank",
        "title": titles.get(status_code, "Error"),
        "status": status_code,
        "detail": detail,
        "instance": path,
        "properties": {
            "timestamp": datetime.now(UTC).isoformat(),
            "code": code,
        },
    }


def register_domain_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EntityNotFoundException)
    async def entity_not_found(request: Request, exc: EntityNotFoundException) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_problem(404, exc.message, request.url.path, exc.code),
            media_type="application/problem+json",
        )

    @app.exception_handler(ConflictException)
    async def conflict(request: Request, exc: ConflictException) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_problem(409, exc.message, request.url.path, exc.code),
            media_type="application/problem+json",
        )

    @app.exception_handler(BusinessRuleViolationException)
    async def business_rule(request: Request, exc: BusinessRuleViolationException) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_problem(400, exc.message, request.url.path, exc.code),
            media_type="application/problem+json",
        )

    @app.exception_handler(InsufficientDataException)
    async def insufficient_data(request: Request, exc: InsufficientDataException) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_problem(422, exc.message, request.url.path, exc.code),
            media_type="application/problem+json",
        )

    @app.exception_handler(DomainException)
    async def domain_exception(request: Request, exc: DomainException) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_problem(400, exc.message, request.url.path, exc.code),
            media_type="application/problem+json",
        )
