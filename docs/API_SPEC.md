# FarmU API Specification v1

기준일: 2026-06-15  
현재 Base URL: `http://43.202.51.195`  
HTTPS 목표 Base URL: `https://{DOMAIN}`

## 1. 공통 규칙

### 인증

- 보호 API: `Authorization: Bearer {accessToken}`
- Access Token: 프론트엔드 메모리 저장
- Refresh Token: `refresh_token` httpOnly Cookie
- 프론트 요청은 `credentials: include` 또는 `withCredentials: true` 사용
- Access Token 만료 시 `POST /api/v1/auth/refresh` 후 원 요청을 1회 재시도

### 데이터 규칙

- 페이지는 0부터 시작하며 기본 크기는 20이다.
- 일자는 `yyyy-MM-dd`, 월은 `yyyy-MM`이다.
- 역할은 `UNION_ADMIN`, `CONSULTANT`, `MEMBER`다.
- 성과 그룹은 `TOP`, `MID`, `LOW`다.
- 표시용 점수와 비율은 0~100이다.
- 모델 신뢰도, 위험 점수, 입력 면적 비율은 0~1이다.
- 금액은 원 단위 정수다.
- `period` 생략을 지원하는 API는 최신 집계월을 사용한다.

### 성공 응답

```json
{ "data": {} }
```

페이지 응답:

```json
{
  "data": [],
  "page": 0,
  "size": 20,
  "totalElements": 0,
  "totalPages": 0,
  "hasNext": false
}
```

### 오류 응답

모든 HTTP·도메인·검증 오류는 RFC 9457 형식이다.

```json
{
  "type": "about:blank",
  "title": "Bad Request",
  "status": 400,
  "detail": "잘못된 요청입니다.",
  "instance": "/api/v1/example",
  "properties": {
    "timestamp": "2026-06-12T00:00:00Z",
    "code": "INVALID_REQUEST"
  }
}
```

## 2. 인증

### `POST /api/v1/auth/login`

```json
{ "loginId": "farmu01", "password": "password", "unionCode": "U001" }
```

응답은 `accessToken`, `expiresIn`, `user`를 반환하고 Refresh Token 쿠키를 설정한다.

### `POST /api/v1/auth/refresh`

Refresh Token 쿠키로 토큰을 회전한다. 기존 클라이언트는 본문의 `refreshToken`도 사용할 수 있다.

### `POST /api/v1/auth/logout`

Access Token과 Refresh Token을 폐기하고 `204`를 반환한다.

### `POST /api/v1/auth/register`

조합 가입용 관리자 계정을 생성한다.

### `POST /api/v1/auth/users`

`UNION_ADMIN`이 `MEMBER`, `CONSULTANT`, `UNION_ADMIN` 계정을 생성한다.

### `GET /api/v1/auth/me`

기존 클라이언트 호환용 현재 사용자 조회 경로다.

## 3. 사용자와 프로필

### `GET /api/v1/users/me`

사용자, 권한, 연결된 `memberId`, 연락처, 소개, 이미지 URL을 반환한다.

### `PATCH /api/v1/users/me`

```json
{
  "name": "김농부",
  "phone": "010-1234-5678",
  "email": "farmer@example.com",
  "bio": "사과 재배 7년차"
}
```

보낸 필드만 갱신한다.

### `PATCH /api/v1/users/me/password`

```json
{ "currentPassword": "old-password", "newPassword": "new-password" }
```

### `PATCH /api/v1/users/me/images`

`multipart/form-data`의 `avatar`, `banner`를 지원한다. 이미지별 최대 크기는 5MB다.

### `GET /api/v1/users/me/notifications`

알림 수신 설정을 반환한다.

### `PUT /api/v1/users/me/notifications`

```json
{
  "settings": [
    { "key": "RISK_ALERT", "channels": ["PUSH", "EMAIL"], "enabled": true }
  ]
}
```

### `PUT /api/v1/users/{userId}/member`

`UNION_ADMIN`이 사용자와 조합원 엔터티를 연결한다.

## 4. 헤더 기능

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/notifications/unread-count` | 읽지 않은 알림 수 |
| GET | `/api/v1/notifications?size=10` | 최근 알림 |
| PATCH | `/api/v1/notifications/{id}/read` | 단일 읽음 처리 |
| PATCH | `/api/v1/notifications/read-all` | 전체 읽음 처리 |
| GET | `/api/v1/search?q={query}&size=10` | 조합원·필지·리포트 검색 |

검색 결과 타입은 `MEMBER`, `LAND`, `REPORT`이며 내부 `actionUrl`을 포함한다.

## 5. 대시보드

### `GET /api/v1/dashboard/summary`

Query: `unionId`, `period?`  
평균 점수, 그룹 분포 `top/mid/low`, 출하 적중률, 평균 수익, 리포트 단축률과
`availablePeriods`를 반환한다.

### `GET /api/v1/dashboard/trends`

Query: `unionId`, `from`, `to`, `metric`  
`metric`: `score`, `revenue`, `shippingHitRate`, `production`

```json
{
  "data": {
    "metric": "score",
    "series": [
      { "name": "AVERAGE", "points": [{ "period": "2026-05", "value": 75 }] },
      { "name": "TOP", "points": [{ "period": "2026-05", "value": 90 }] },
      { "name": "LOW", "points": [{ "period": "2026-05", "value": 60 }] }
    ]
  }
}
```

### `GET /api/v1/dashboard/alerts`

Query: `unionId`, `level?`, `status?`, `page=0`, `size=10`

### `PATCH /api/v1/dashboard/alerts/{alertId}`

```json
{ "status": "DISMISSED" }
```

## 6. 조합원 분석

### `GET /api/v1/members/ranking`

Query: `unionId`, `period?`, `group=ALL`, `page=0`, `size=20`  
`group`: `ALL`, `TOP`, `MID`, `LOW`

### `GET /api/v1/members/{memberId}/analysis`

Query: `period?`  
프로필, 총점, 전월 변화, 순위, 생산·출하·수익·품질·비용효율 점수, 점수 추이,
작목 적합도, XAI 요인과 baseline, 개선 과제, `availablePeriods`를 반환한다.

- `ScoreDetail.score`: 가중 반영 점수
- `ScoreDetail.value`: UI 막대용 0~100 값
- `quality`, `costEfficiency`: 현재 생산·출하·수익 점수에서 계산한 파생 지표
- `years`: 조합원 등록 연도 기준 영농 연차
- `baseline + sum(xaiFactors.contribution) = totalScore`

### `GET /api/v1/members/me/analysis`

로그인 사용자와 연결된 조합원의 분석을 반환한다. 사용자-조합원 연결이 없으면 404다.

## 7. 출하 추천

### `GET /api/v1/shipping/recommendations`

Query: `unionId?`, `memberId?`, `status?`

### `POST /api/v1/shipping/recommendations/{id}/decision`

```json
{ "decision": "ACCEPTED", "actualShipDate": "2026-06-12", "memo": "확정" }
```

`decision`: `ACCEPTED`, `REJECTED`

### `GET /api/v1/shipping/accuracy`

Query: `unionId`, `from`, `to`  
월별 및 전체 적중률을 0~100 값으로 반환한다.

## 8. 필지와 작목

### `GET /api/v1/lands`

Query: `memberId?`, `page=0`, `size=20`  
네이버지도에서 사용할 위도·경도, 주소, 면적, 주 작목을 반환한다.

### `GET /api/v1/lands/{landId}/suitability`

후보 작목별 적합도 점수와 근거를 반환한다.

## 9. 개선 시나리오

시뮬레이션 요청:

```json
{
  "memberId": "mem_001",
  "landId": "land_001",
  "changes": {
    "fromCrop": "사과",
    "toCrop": "복숭아",
    "applyAreaRatio": 0.5,
    "startPeriod": "2026-06"
  }
}
```

시뮬레이션 응답의 `scenarioId`를 저장 요청에 사용한다.

```json
{ "scenarioId": "scn_...", "name": "복숭아 전환" }
```

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/api/v1/scenarios/simulate` | 저장하지 않고 결과 계산 |
| POST | `/api/v1/scenarios` | 시나리오 저장 |
| GET | `/api/v1/scenarios?memberId={id}` | 저장된 시나리오 조회 |
| DELETE | `/api/v1/scenarios/{scenarioId}` | 시나리오 삭제 |

결과는 예상 수익 변화율, 점수 변화, 위험 수준, 연간 수익 변화액을 포함한다.

## 10. 멘토링

### `GET /api/v1/mentoring/suggestions?menteeId={id}`

같은 조합에서 성과 점수가 높은 멘토 후보와 `matchReasons`, 추정 `distanceKm`를 반환한다.
`score`는 멘토의 최신 종합 성과 점수(0~100)다.

### `GET /api/v1/mentoring/suggestions/{mentorId}?menteeId={id}`

멘토 경력, 거리, 매칭 사유·태그·요인, 멘티/멘토 구성 점수 비교와 구조화된 도움 영역을 반환한다.
실제 좌표 기반 거리가 없는 경우 지역 문자열 기반 추정값을 사용한다.

### `POST /api/v1/mentoring/matches`

```json
{
  "menteeId": "mem_001",
  "mentorId": "mem_002",
  "goal": "생산량 개선"
}
```

`helpAreas` 배열도 선택적으로 함께 전송할 수 있다.

추가 경로:

- `GET /api/v1/mentoring/suggestions/{mentorId}`
- `PATCH /api/v1/mentoring/matches/{matchId}/reject`
- `GET|POST /api/v1/mentoring/matches/{matchId}/tasks`
- `PATCH /api/v1/mentoring/matches/{matchId}/tasks/{taskId}`

도움 영역: `PRODUCTION`, `SHIPPING`, `REVENUE`, `QUALITY`, `COST`,
`CROP_CHANGE`, `CONNECT`

### `PATCH /api/v1/mentoring/matches/{id}/approve`

`UNION_ADMIN`, `CONSULTANT`가 대기 중 매칭을 승인한다.

## 11. 리포트

### `POST /api/v1/reports/generate`

```json
{
  "type": "MEMBER",
  "format": "PDF",
  "sections": ["SUMMARY", "XAI"],
  "period": "2026-05",
  "unionId": "uni_001",
  "memberId": "mem_001"
}
```

`type`: `MEMBER`, `UNION`, `MONTHLY`  
`format`: `PDF`, `CSV`, `XLSX`  
기존 `reportType` 필드도 하위 호환으로 허용한다.

`202` 작업 응답을 반환한다.

### `GET /api/v1/reports/{id}`

상태와 10분 만료 서명 `downloadUrl`을 반환한다.

### `GET /api/v1/reports/{id}/download`

Query: `expires`, `signature`  
서명이 유효하면 `application/pdf` 파일을 반환한다.

### `GET /api/v1/reports`

Query: `period?`, `page=0`, `size=20`

## 12. 데이터 관리

모든 API는 `UNION_ADMIN` 전용이다.

### `POST /api/v1/data/uploads`

```json
{
  "fileName": "members.csv",
  "dataType": "text/csv",
  "size": 2048
}
```

15분 유효한 `uploadUrl`, `method: PUT`, 전송 헤더를 반환한다. 프론트는 반환된 URL로
파일 원문을 PUT한 후 validation API를 조회한다. `.csv`, `.xlsx`, 최대 20MB다.
기존 `filename`, `contentType` 키도 하위 호환으로 허용한다.

기존 multipart 직접 업로드는 `POST /api/v1/data/uploads/direct`에서 지원한다.

### `GET /api/v1/data/uploads`

업로드 이력을 페이지 조회한다.

### `GET /api/v1/data/uploads/{id}/validation`

파일 검증 상태, 행 수, 오류 목록을 반환한다.

### `PATCH /api/v1/data/uploads/{id}/rows/{row}`

```json
{ "values": { "name": "김농부", "crop": "사과" } }
```

### `POST /api/v1/data/uploads/{id}/revalidate`

수정된 행을 반영해 유효성을 다시 계산한다.

### `POST /api/v1/data/uploads/{id}/commit`

`VALIDATED` 업로드를 최종 반영 상태 `APPLIED`로 변경한다.
기존 `/apply` 경로는 deprecated 별칭으로 유지한다.

## 13. 가중치 설정

### `GET /api/v1/settings/weights`

현재 조합의 생산·출하·수익 가중치를 반환한다.

### `PATCH /api/v1/settings/weights`

`UNION_ADMIN` 전용이며 합계가 반드시 100이어야 한다.

```json
{ "production": 40, "shipping": 30, "revenue": 30 }
```

## 14. 주요 오류 코드

| Code | HTTP | 설명 |
| --- | --- | --- |
| INVALID_REQUEST | 400 | 잘못된 요청 |
| INVALID_CREDENTIALS | 401 | 로그인 정보 불일치 |
| INVALID_REFRESH_TOKEN | 401 | Refresh Token 오류 |
| FORBIDDEN_ROLE | 403 | 역할 권한 부족 |
| NOT_FOUND | 404 | 리소스 없음 |
| CONFLICT | 409 | 현재 상태와 충돌 |
| FILE_TOO_LARGE | 413 | 업로드 크기 초과 |
| UNSUPPORTED_FILE_TYPE | 415 | 지원하지 않는 파일 |
| VALIDATION_FAILED | 422 | 데이터 검증 실패 |
| INTERNAL_SERVER_ERROR | 500 | 서버 내부 오류 |

## 15. 구현 및 검증 상태

- 프론트 MVP 명세에 기재된 API 구현 완료
- Alembic `001 → 004` 빈 DB 적용 완료
- 단위·통합 테스트 16개 통과
- 신규 코드 Ruff 검사 통과 (`N803`, `N815`, `E501`은 JSON camelCase 계약과 기존 정책상 제외)
- 신규 코드 mypy 검사 통과
- 저장소 전체에는 기존 Ruff/mypy 품질 부채가 남아 있다.

## 16. Gemini AI

- 공급자: Google Gemini API
- 모델: `gemini-3.5-flash`
- `POST /api/v1/ai/advice`: 작목, 지역, 주제와 질문을 기반으로 농업 조언 생성
- `GET /api/v1/ai/status`: 모델과 서버 설정 상태 조회
- `POST /api/v1/scenarios/simulate`: 기존 수치 계산에 Gemini 해설과 위험 요인을 추가
- Gemini 장애 시 시나리오 수치 계산은 유지되며 `aiAdvice`가 `null`로 반환된다.
