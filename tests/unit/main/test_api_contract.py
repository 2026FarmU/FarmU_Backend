from src.auth.adapter.http.schema.auth_schema import LoginResponse, RefreshResponse
from src.data_ingest.adapter.http.router.data_router import CreateUploadRequest
from src.main.app import create_app


def test_frontend_contract_routes_are_registered() -> None:
    app = create_app()
    routes = {(method, route.path) for route in app.routes for method in route.methods or []}

    expected = {
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/refresh"),
        ("POST", "/api/v1/auth/logout"),
        ("GET", "/api/v1/users/me"),
        ("PATCH", "/api/v1/users/me"),
        ("PATCH", "/api/v1/users/me/password"),
        ("GET", "/api/v1/notifications/unread-count"),
        ("GET", "/api/v1/notifications"),
        ("PATCH", "/api/v1/notifications/{notification_id}/read"),
        ("PATCH", "/api/v1/notifications/read-all"),
        ("GET", "/api/v1/search"),
        ("GET", "/api/v1/members/me/analysis"),
        ("GET", "/api/v1/lands"),
        ("GET", "/api/v1/lands/{land_id}/suitability"),
        ("POST", "/api/v1/scenarios/simulate"),
        ("POST", "/api/v1/scenarios"),
        ("GET", "/api/v1/scenarios"),
        ("DELETE", "/api/v1/scenarios/{scenario_id}"),
        ("GET", "/api/v1/mentoring/suggestions"),
        ("GET", "/api/v1/mentoring/suggestions/{mentor_id}"),
        ("POST", "/api/v1/mentoring/matches"),
        ("PATCH", "/api/v1/mentoring/matches/{match_id}/approve"),
        ("PATCH", "/api/v1/mentoring/matches/{match_id}/reject"),
        ("GET", "/api/v1/mentoring/matches/{match_id}/tasks"),
        ("POST", "/api/v1/mentoring/matches/{match_id}/tasks"),
        ("PATCH", "/api/v1/mentoring/matches/{match_id}/tasks/{task_id}"),
        ("POST", "/api/v1/reports/generate"),
        ("GET", "/api/v1/reports/{report_id}"),
        ("GET", "/api/v1/reports"),
        ("POST", "/api/v1/data/uploads"),
        ("PUT", "/api/v1/data/uploads/{upload_id}/content"),
        ("GET", "/api/v1/data/uploads"),
        ("GET", "/api/v1/data/uploads/{upload_id}/validation"),
        ("PATCH", "/api/v1/data/uploads/{upload_id}/rows/{row_number}"),
        ("POST", "/api/v1/data/uploads/{upload_id}/revalidate"),
        ("POST", "/api/v1/data/uploads/{upload_id}/commit"),
        ("POST", "/api/v1/data/uploads/{upload_id}/apply"),
        ("GET", "/api/v1/settings/weights"),
        ("PATCH", "/api/v1/settings/weights"),
        ("GET", "/api/v1/ai/status"),
        ("POST", "/api/v1/ai/advice"),
    }

    assert expected <= routes


def test_refresh_token_is_not_exposed_in_success_schemas() -> None:
    assert "refreshToken" not in LoginResponse.model_json_schema()["properties"]
    assert "refreshToken" not in RefreshResponse.model_json_schema()["properties"]


def test_custom_swagger_has_korean_operation_descriptions() -> None:
    schema = create_app().openapi()
    operation = schema["paths"]["/api/v1/scenarios/simulate"]["post"]

    assert operation["summary"] == "작목 전환 시뮬레이션"
    assert "Gemini 3.5 Flash" in operation["description"]
    assert schema["servers"][0]["url"]


def test_every_json_success_response_has_a_schema() -> None:
    schema = create_app().openapi()
    missing: list[tuple[str, str, str]] = []
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            for code, response in operation.get("responses", {}).items():
                if not str(code).startswith("2") or str(code) == "204":
                    continue
                content = response.get("content", {}).get("application/json")
                if content is not None and not content.get("schema"):
                    missing.append((method, path, str(code)))
    assert missing == []


def test_upload_request_accepts_frontend_and_legacy_field_names() -> None:
    frontend = CreateUploadRequest.model_validate(
        {"fileName": "members.csv", "dataType": "text/csv", "size": 10}
    )
    legacy = CreateUploadRequest.model_validate(
        {"filename": "members.csv", "contentType": "text/csv", "size": 10}
    )

    assert frontend.fileName == legacy.fileName == "members.csv"
    assert frontend.dataType == legacy.dataType == "text/csv"
