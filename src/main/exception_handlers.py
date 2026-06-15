from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse


def _problem_detail(
    status_code: int,
    detail: str,
    instance: str,
    code: str,
) -> dict[str, object]:
    return {
        "type": "about:blank",
        "title": _status_title(status_code),
        "status": status_code,
        "detail": detail,
        "instance": instance,
        "properties": {
            "timestamp": datetime.now(UTC).isoformat(),
            "code": code,
        },
    }


def _status_title(status_code: int) -> str:
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        413: "Payload Too Large",
        415: "Unsupported Media Type",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
        502: "Bad Gateway",
    }
    return titles.get(status_code, "Error")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> ORJSONResponse:
        code_by_status = {
            400: "INVALID_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN_ROLE",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "FILE_TOO_LARGE",
            415: "UNSUPPORTED_FILE_TYPE",
            422: "VALIDATION_FAILED",
        }
        return ORJSONResponse(
            status_code=exc.status_code,
            content=_problem_detail(
                exc.status_code,
                str(exc.detail),
                request.url.path,
                code_by_status.get(exc.status_code, "HTTP_ERROR"),
            ),
            media_type="application/problem+json",
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = ".".join(str(loc) for loc in first.get("loc", [])[1:])
        msg = first.get("msg", "유효성 검증 실패")
        detail = f"{field}: {msg}" if field else msg

        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_problem_detail(400, detail, str(request.url.path), "INVALID_REQUEST"),
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_problem_detail(
                500,
                "서버 내부 오류가 발생했습니다.",
                str(request.url.path),
                "INTERNAL_SERVER_ERROR",
            ),
            media_type="application/problem+json",
        )
