from typing import Any

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from starlette.responses import HTMLResponse

from src.main.config import get_settings

TAGS_METADATA = [
    {"name": "auth", "description": "로그인, 토큰 재발급, 로그아웃 및 관리자 사용자 생성"},
    {"name": "users", "description": "현재 사용자 프로필, 비밀번호, 이미지, 알림 수신 설정"},
    {"name": "dashboard", "description": "조합 KPI, 월별 추이와 위험 알림"},
    {"name": "members", "description": "조합원 랭킹과 성과/XAI 분석"},
    {"name": "shipping", "description": "출하 시점 추천, 의사결정 및 적중률"},
    {"name": "lands", "description": "필지 위치와 후보 작목 적합도"},
    {"name": "scenarios", "description": "작목 전환 시뮬레이션과 Gemini AI 해설"},
    {"name": "mentoring", "description": "멘토 추천, 매칭 요청 및 승인"},
    {"name": "reports", "description": "리포트 생성, 상태 조회와 서명 다운로드"},
    {"name": "data", "description": "관리자 CSV/XLSX 업로드, 검증 및 반영"},
    {"name": "notifications", "description": "헤더 알림 목록과 읽음 처리"},
    {"name": "search", "description": "조합원, 필지, 리포트 통합 검색"},
    {"name": "settings", "description": "조합 성과 가중치 설정"},
    {"name": "ai", "description": "Google Gemini 3.5 Flash 기반 농업 조언"},
    {"name": "health", "description": "배포 및 로드밸런서 상태 확인"},
]

OPERATION_DOCS: dict[str, tuple[str, str]] = {
    "register": (
        "조합 관리자 회원가입",
        "조합 코드를 확인하고 최초 UNION_ADMIN 계정을 생성합니다.",
    ),
    "create_user": (
        "조합 사용자 생성",
        "UNION_ADMIN이 같은 조합의 MEMBER, CONSULTANT 또는 관리자를 생성합니다.",
    ),
    "login": ("로그인", "Access Token을 반환하고 Refresh Token을 httpOnly 쿠키로 설정합니다."),
    "refresh": ("Access Token 재발급", "Refresh Token 쿠키를 검증하고 두 토큰을 회전합니다."),
    "logout": ("로그아웃", "Access Token을 차단하고 저장된 Refresh Token과 쿠키를 삭제합니다."),
    "get_me": ("현재 인증 사용자 조회", "기존 클라이언트 호환용 사용자/권한 조회 API입니다."),
    "get_my_profile": ("내 프로필 조회", "프로필, 권한, 조합 및 연결된 조합원 ID를 반환합니다."),
    "update_my_profile": (
        "내 프로필 수정",
        "이름, 연락처, 이메일, 소개 중 전송한 값을 수정합니다.",
    ),
    "change_my_password": ("비밀번호 변경", "현재 비밀번호를 확인한 뒤 새 비밀번호로 변경합니다."),
    "update_my_images": (
        "프로필 이미지 변경",
        "avatar 또는 banner 이미지 파일을 최대 5MB까지 받습니다.",
    ),
    "get_notification_settings": (
        "알림 수신 설정 조회",
        "푸시와 이메일 채널별 수신 설정을 조회합니다.",
    ),
    "update_notification_settings": (
        "알림 수신 설정 저장",
        "현재 사용자의 알림 설정 전체를 교체합니다.",
    ),
    "link_user_member": (
        "사용자-조합원 연결",
        "관리자가 로그인 사용자와 분석 대상 조합원을 연결합니다.",
    ),
    "get_summary": (
        "대시보드 KPI 조회",
        "최신 또는 지정 월의 KPI와 선택 가능한 기간을 반환합니다.",
    ),
    "get_trends": (
        "대시보드 다중 추이 조회",
        "기간과 지표에 따른 AVERAGE, TOP, LOW 세 개의 월별 시계열을 한 번에 반환합니다.",
    ),
    "get_alerts": ("위험 알림 조회", "레벨과 상태로 필터링한 조합 위험 알림을 페이지 조회합니다."),
    "dismiss_alert": (
        "위험 알림 해제",
        "관리자 또는 컨설턴트가 알림을 DISMISSED 상태로 변경합니다.",
    ),
    "get_ranking": (
        "조합원 랭킹 조회",
        "TOP/MID/LOW 그룹과 기간으로 조합원 성과 순위를 조회합니다.",
    ),
    "get_my_analysis": ("내 성과 분석 조회", "로그인 사용자와 연결된 조합원의 분석을 반환합니다."),
    "get_analysis": (
        "조합원 상세 분석 조회",
        "프로필, 순위, 5개 구성 점수, 점수 추이, 작목 적합도, XAI baseline과 개선 과제를 반환합니다.",
    ),
    "get_recommendations": ("출하 추천 조회", "조합원과 상태 기준으로 출하 추천을 조회합니다."),
    "decide_recommendation": (
        "출하 추천 채택/거절",
        "PENDING 추천에 ACCEPTED 또는 REJECTED 결정을 기록합니다.",
    ),
    "get_accuracy": ("출하 적중률 조회", "기간별 출하 추천 적중률을 0~100 값으로 반환합니다."),
    "get_unread_count": ("읽지 않은 알림 수", "현재 사용자의 미확인 알림 개수를 반환합니다."),
    "get_notifications": ("최근 알림 조회", "현재 사용자의 최근 알림을 생성 역순으로 반환합니다."),
    "read_all_notifications": (
        "알림 전체 읽음",
        "현재 사용자의 미확인 알림을 모두 읽음 처리합니다.",
    ),
    "read_notification": ("알림 단일 읽음", "지정한 알림을 읽음 처리합니다."),
    "global_search": ("통합 검색", "현재 조합의 조합원, 필지, 리포트를 검색합니다."),
    "get_lands": ("필지 목록 조회", "지도 표시용 위치, 주소, 면적과 주 작목을 반환합니다."),
    "get_suitability": ("필지 작목 적합도 조회", "후보 작목별 0~100 적합도와 근거를 반환합니다."),
    "simulate_scenario": (
        "작목 전환 시뮬레이션",
        "계산 결과와 Gemini 3.5 Flash의 실행 조언을 반환합니다.",
    ),
    "save_scenario": ("시나리오 저장", "시뮬레이션 결과와 AI 해설을 저장합니다."),
    "get_scenarios": ("저장 시나리오 조회", "현재 조합의 시나리오를 최신순으로 반환합니다."),
    "delete_scenario": ("시나리오 삭제", "현재 조합에 저장된 시나리오를 영구 삭제합니다."),
    "get_suggestions": ("멘토 후보 추천", "같은 조합의 고성과 조합원을 멘토 후보로 추천합니다."),
    "get_suggestion_detail": (
        "멘토 상세 조회",
        "추천 멘토의 경력, 거리, 매칭 요인, 멘티 비교와 구조화된 도움 영역을 조회합니다.",
    ),
    "create_match": ("멘토링 매칭 요청", "멘티, 멘토와 도움 영역으로 PENDING 매칭을 생성합니다."),
    "approve_match": ("멘토링 매칭 승인", "관리자 또는 컨설턴트가 매칭을 승인합니다."),
    "reject_match": ("멘토링 매칭 거절", "PENDING 상태의 매칭 요청을 거절합니다."),
    "get_tasks": ("멘토링 과제 목록", "매칭에 등록된 실행 과제를 생성 순으로 조회합니다."),
    "create_task": ("멘토링 과제 생성", "승인된 매칭에 실행 과제를 추가합니다."),
    "update_task": ("멘토링 과제 수정", "과제 내용, 기한 또는 완료 상태를 수정합니다."),
    "generate_report": ("리포트 생성", "리포트를 생성하고 조회용 작업 ID를 반환합니다."),
    "get_report": ("리포트 상태 조회", "상태와 10분 만료 서명 다운로드 URL을 반환합니다."),
    "download_report": ("리포트 다운로드", "유효한 만료 시각과 서명을 검증한 뒤 PDF를 반환합니다."),
    "get_reports": ("리포트 목록 조회", "현재 조합의 리포트를 기간별로 페이지 조회합니다."),
    "create_upload": ("업로드 URL 발급", "파일 메타데이터를 등록하고 15분 유효한 서명 PUT URL을 반환합니다."),
    "put_upload_content": ("서명 URL 파일 전송", "발급받은 uploadUrl로 CSV/XLSX 원문을 PUT 전송합니다."),
    "upload_data_direct": ("직접 파일 업로드(호환)", "기존 클라이언트용 multipart 직접 업로드 경로입니다."),
    "get_uploads": ("업로드 이력 조회", "현재 조합의 업로드, 검증 및 반영 상태를 페이지 조회합니다."),
    "get_validation": ("업로드 검증 결과 조회", "행 수와 검증 오류를 반환합니다."),
    "correct_upload_row": ("검증 오류 행 수정", "오류 행의 교정 값을 저장하고 해당 행 오류를 제거합니다."),
    "revalidate_upload": ("업로드 재검증", "교정된 행을 포함해 업로드 유효성을 다시 계산합니다."),
    "commit_upload": ("검증 데이터 반영", "VALIDATED 업로드를 최종 APPLIED 상태로 변경합니다."),
    "apply_upload": ("검증 데이터 최종 반영", "VALIDATED 업로드를 APPLIED 상태로 변경합니다."),
    "get_weights": ("성과 가중치 조회", "현재 조합의 생산, 출하, 수익 가중치를 반환합니다."),
    "update_weights": ("성과 가중치 수정", "합계 100인 가중치를 UNION_ADMIN이 저장합니다."),
    "get_ai_status": (
        "AI 서비스 상태 조회",
        "Gemini 공급자, 모델과 API 키 설정 여부를 반환합니다.",
    ),
    "create_farm_advice": (
        "AI 농업 조언 생성",
        "질문과 영농 문맥을 Gemini 3.5 Flash로 분석합니다.",
    ),
    "health_check": ("서버 상태 확인", "프로세스가 요청을 처리할 수 있는지 확인합니다."),
}


def configure_api_docs(app: FastAPI) -> None:
    settings = get_settings()
    for route in app.routes:
        if isinstance(route, APIRoute) and route.name in OPERATION_DOCS:
            route.summary, route.description = OPERATION_DOCS[route.name]

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title="FarmU Backend API",
            version=settings.app_version,
            description=(
                "팜유 프론트엔드 MVP 연동용 API입니다.\n\n"
                "**인증 순서**: 로그인 → 응답의 Access Token을 Authorize에 입력 → "
                "401 발생 시 refresh 호출. Refresh Token은 httpOnly 쿠키로 관리됩니다.\n\n"
                "**공통 규칙**: 페이지는 0부터 시작하며, 월은 yyyy-MM, 일자는 yyyy-MM-dd입니다. "
                "표시용 점수와 비율은 0~100입니다.\n\n"
                "**성공 응답 규약**: 단건은 `{ data: X }`, 목록은 `{ data: X[] }`, "
                "페이지 목록은 `{ data: X[], page, size, totalElements, totalPages, hasNext }`입니다. "
                "204와 파일 다운로드는 envelope를 사용하지 않습니다."
            ),
            routes=app.routes,
            tags=TAGS_METADATA,
            servers=[{"url": settings.public_base_url, "description": "현재 배포 서버"}],
        )
        schema["info"]["contact"] = {"name": "FarmU Backend Team"}
        schema["info"]["license"] = {"name": "Private MVP"}
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        components["GenericSuccessData"] = {
            "type": "object",
            "required": ["data"],
            "properties": {
                "data": {
                    "oneOf": [
                        {"type": "object", "additionalProperties": True},
                        {"type": "array", "items": {}},
                    ],
                    "description": "엔드포인트별 성공 데이터",
                }
            },
        }
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                if operation.get("operationId", "").startswith("download_report"):
                    continue
                for code, response in operation.get("responses", {}).items():
                    if not str(code).startswith("2") or str(code) == "204":
                        continue
                    content = response.setdefault("content", {}).setdefault(
                        "application/json", {}
                    )
                    if not content.get("schema"):
                        content["schema"] = {
                            "$ref": "#/components/schemas/GenericSuccessData"
                        }
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    if settings.docs_enabled:

        @app.get("/docs", include_in_schema=False)
        async def swagger_ui() -> HTMLResponse:
            return get_swagger_ui_html(
                openapi_url=app.openapi_url or "/openapi.json",
                title="FarmU API 문서",
                swagger_ui_parameters={
                    "persistAuthorization": True,
                    "displayRequestDuration": True,
                    "filter": True,
                    "docExpansion": "none",
                    "defaultModelsExpandDepth": 1,
                    "tryItOutEnabled": True,
                },
            )

        @app.get("/redoc", include_in_schema=False)
        async def redoc_ui() -> HTMLResponse:
            return get_redoc_html(
                openapi_url=app.openapi_url or "/openapi.json",
                title="FarmU API Reference",
            )
