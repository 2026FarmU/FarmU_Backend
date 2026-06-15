from typing import Literal

from fastapi import APIRouter, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.ai.gemini_client import GeminiClient, GeminiUnavailableError
from src.main.response_schema import DataResponse

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class FarmAdviceRequest(BaseModel):
    topic: Literal["PRODUCTION", "SHIPPING", "REVENUE", "QUALITY", "COST", "CROP_CHANGE"]
    question: str = Field(min_length=5, max_length=2000)
    crop: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=200)
    context: dict[str, object] = Field(default_factory=dict)


class AiStatusResponse(BaseModel):
    provider: str
    model: str
    configured: bool


class FarmAdviceResponse(BaseModel):
    summary: str
    recommendations: list[str]
    risks: list[str]
    confidence: float
    provider: str
    model: str


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="AI 서비스 상태 조회",
    response_model=DataResponse[AiStatusResponse],
)
async def get_ai_status(current: CurrentUser) -> ORJSONResponse:
    client = GeminiClient()
    return ORJSONResponse(
        {
            "data": {
                "provider": "Google Gemini",
                "model": client.model,
                "configured": client.configured,
            }
        }
    )


@router.post(
    "/advice",
    status_code=status.HTTP_200_OK,
    summary="AI 농업 조언 생성",
    response_model=DataResponse[FarmAdviceResponse],
)
async def create_farm_advice(
    body: FarmAdviceRequest,
    current: CurrentUser,
) -> ORJSONResponse:
    client = GeminiClient()
    prompt = (
        f"주제: {body.topic}\n작목: {body.crop or '미지정'}\n"
        f"지역: {body.region or '미지정'}\n질문: {body.question}\n"
        f"추가 데이터: {body.context}\n\n"
        "다음 JSON 객체만 반환하세요: "
        '{"summary":"한 줄 요약","recommendations":["실행 항목"],'
        '"risks":["주의 사항"],"confidence":0}'
    )
    try:
        result = await client.generate_json(
            system_instruction=(
                "당신은 한국 농업협동조합의 영농 컨설턴트입니다. "
                "근거가 부족하면 단정하지 말고 안전하고 실행 가능한 조언을 한국어로 제공합니다."
            ),
            prompt=prompt,
        )
    except GeminiUnavailableError as exc:
        return ORJSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "type": "about:blank",
                "title": "Service Unavailable",
                "status": 503,
                "detail": str(exc),
                "properties": {"code": "AI_SERVICE_UNAVAILABLE"},
            },
            media_type="application/problem+json",
        )
    return ORJSONResponse(
        {
            "data": {
                **result,
                "provider": "Google Gemini",
                "model": client.model,
            }
        }
    )
