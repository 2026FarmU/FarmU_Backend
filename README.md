# FarmU Server

농업 성과 관리 플랫폼 **팜유(FarmU)** 백엔드 API 서버입니다.

---

## 목차

1. [기술 스택](#기술-스택)
2. [아키텍처](#아키텍처)
3. [프로젝트 구조](#프로젝트-구조)
4. [개발 환경 설정](#개발-환경-설정)
5. [실행 방법](#실행-방법)
6. [DB 마이그레이션](#db-마이그레이션)
7. [테스트](#테스트)
8. [코드 품질](#코드-품질)
9. [환경변수 레퍼런스](#환경변수-레퍼런스)
10. [Makefile 커맨드](#makefile-커맨드)
11. [AWS 인프라](#aws-인프라)
12. [API 개요](#api-개요)

---

## 기술 스택

| 항목 | 기술 |
|---|---|
| 언어 | Python 3.12 |
| 프레임워크 | FastAPI |
| 아키텍처 | DDD + Hexagonal Architecture |
| ORM | SQLAlchemy 2.0 (async) |
| DB | PostgreSQL 16 + PostGIS |
| 마이그레이션 | Alembic |
| 인증 | JWT (python-jose) |
| AI | scikit-learn, LightGBM, SHAP, Prophet |
| 비동기 작업 | Celery + Redis |
| 캐시 | Redis |
| 빌드 | Poetry |
| 배포 | AWS ECS Fargate |

---

## 아키텍처

### 헥사고날 아키텍처 (Ports & Adapters)

```
┌─────────────────────────────────────────────────┐
│                   Adapter Layer                  │
│  HTTP Router │ ORM Repository │ External API     │
└──────────────────────┬──────────────────────────┘
                       │ (inbound port 호출)
┌──────────────────────▼──────────────────────────┐
│               Application Layer                  │
│  UseCase Service │ Port Interface (provided/required) │
└──────────────────────┬──────────────────────────┘
                       │ (outbound port 사용)
┌──────────────────────▼──────────────────────────┐
│                  Domain Layer                    │
│   Entity │ Domain Service │ Repository Interface │
│         (순수 비즈니스 로직 — 외부 의존 없음)       │
└─────────────────────────────────────────────────┘
```

**핵심 원칙**

- 의존성 방향: `adapter → application → domain` (단방향)
- 도메인 레이어는 FastAPI, SQLAlchemy, Pydantic 등 외부 기술에 의존하지 않음
- Pydantic 스키마는 `adapter/http/schema/` 에서만 사용
- BC(Bounded Context) 간 직접 `import` 금지 → UseCase 호출 또는 도메인 이벤트로만 통신

### BC (Bounded Context) 목록

| BC | 설명 |
|---|---|
| `auth` | 로그인, JWT, 권한 관리 |
| `union` | 조합, 가중치 산식, 평가 기간 |
| `member` | 조합원 프로필, 그룹 분류 |
| `performance` | 성과율 산정, XAI 원인 분석, 개선 과제 |
| `shipping` | 출하 시점 예측, 적중률 추적 |
| `land` | 필지, 작목 적합도 |
| `scenario` | 작목 전환 시뮬레이션 |
| `mentoring` | 매칭, 코디네이터 승인, 공동 과제 |
| `report` | 월간·농가 리포트 비동기 생성 |
| `data_ingest` | 엑셀 업로드, 검증, 공공데이터 어댑터 |
| `alert` | 위험 알림 (가격·기상·수급) |
| `notification` | 푸시·이메일·SMS (후순위) |
| `audit` | 행동 로그 (후순위) |

---

## 개발 환경 설정

### 사전 요구사항

| 도구 | 버전 | 설치 확인 |
|---|---|---|
| Python | 3.12+ | `python3.12 --version` |
| Poetry | 2.x | `poetry --version` |
| Docker Desktop | 최신 | `docker --version` |

**Python 3.12 설치 (macOS)**

```bash
brew install python@3.12
```

**Poetry 설치**

```bash
curl -sSL https://install.python-poetry.org | python3.12 -
# 셸 프로파일에 PATH 추가
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

### 1. 저장소 클론 및 의존성 설치

```bash
git clone <repo-url>
cd server

# Poetry 가상환경 Python 버전 지정
poetry env use python3.12

# 전체 의존성 설치 (dev 포함)
poetry install
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

로컬 개발에서는 기본값 그대로 사용 가능합니다. 필요 시 `.env`를 수정하세요.

### 3. 로컬 인프라 실행 (Docker)

```bash
make docker-up
```

| 서비스 | 주소 | 용도 |
|---|---|---|
| PostgreSQL 16 + PostGIS | `localhost:5432` | 메인 DB |
| Redis 7 | `localhost:6379` | 캐시 / Celery 브로커 |
| MinIO | `localhost:9000` | 로컬 S3 대체 |
| MinIO Console | `localhost:9001` | 버킷 관리 UI |

> MinIO 접속 정보: ID `minioadmin` / PW `minioadmin`

### 4. DB 마이그레이션

```bash
make migrate
```

### 5. pre-commit 훅 설치 (선택)

```bash
make pre-commit-install
```

---

## 실행 방법

### 개발 서버

```bash
make dev
# 또는
poetry run uvicorn src.main.app:app --reload --host 0.0.0.0 --port 8000
```

서버 기동 후 접속:

| URL | 설명 |
|---|---|
| `http://localhost:8000/health` | 헬스체크 |
| `http://localhost:8000/docs` | Swagger UI (`DEBUG=true` 시에만) |
| `http://localhost:8000/redoc` | ReDoc (`DEBUG=true` 시에만) |

### Celery 워커 (비동기 작업)

리포트 생성, 데이터 검증 등 장시간 작업 처리용입니다. 개발 서버와 **별도 터미널**에서 실행합니다.

```bash
make worker
# 또는
poetry run celery -A src.infrastructure.celery.app worker --loglevel=info
```

### 전체 로컬 스택 한번에 올리기

```bash
# 터미널 1 - 인프라
make docker-up

# 터미널 2 - API 서버
make dev

# 터미널 3 - Celery 워커 (필요 시)
make worker
```

---

## DB 마이그레이션

Alembic을 사용하며, **async 드라이버(`asyncpg`)** 기반으로 설정되어 있습니다.

```bash
# 현재 HEAD까지 마이그레이션 적용
make migrate

# 새 마이그레이션 파일 자동 생성 (ORM 모델 변경 후)
make migrate-new msg="add member table"

# 마이그레이션 1단계 롤백
make migrate-down

# 현재 상태 확인
poetry run alembic current

# 마이그레이션 이력 조회
poetry run alembic history --verbose
```

> **주의**: 새 BC의 ORM 모델을 추가했다면 `alembic/env.py` 상단의 import 주석을 해제해야 autogenerate가 감지합니다.

```python
# alembic/env.py
from src.auth.adapter.persistence.model import *   # noqa: F401, F403
from src.union.adapter.persistence.model import *  # noqa: F401, F403
```

---

## 테스트

```bash
# 전체 테스트 + 커버리지
make test

# 단위 테스트만
make test-unit

# 통합 테스트만 (Docker 인프라 필요)
make test-integration

# 특정 파일 또는 마커
poetry run pytest tests/unit/auth -v
poetry run pytest -m "not slow"
```

테스트 구조:

```
tests/
├── unit/            # 외부 의존 없는 순수 단위 테스트
│   └── {bc}/
├── integration/     # DB·Redis 실제 연결 통합 테스트
│   └── {bc}/
└── e2e/             # 전체 HTTP 흐름 테스트
```

---

## 코드 품질

### 린트 & 포맷

```bash
# 검사만
make lint

# 자동 수정
make lint-fix
```

[ruff](https://docs.astral.sh/ruff/)를 사용합니다. 설정은 `pyproject.toml`의 `[tool.ruff]` 섹션을 참고하세요.

### 타입 체크

```bash
make typecheck
# 또는
poetry run mypy src
```

### pre-commit

커밋 시 자동으로 린트·포맷을 검사합니다.

```bash
make pre-commit-install   # 최초 1회 설치
git commit -m "feat: ..."  # 이후 커밋마다 자동 실행
```

---

## 환경변수 레퍼런스

`.env.example`을 복사해 `.env`로 사용합니다. `.env`는 git에 커밋하지 않습니다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `APP_NAME` | `FarmU API` | 앱 이름 |
| `DEBUG` | `false` | Swagger UI 노출 여부 등 |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `DATABASE_URL` | `postgresql+asyncpg://farmu:farmu@localhost:5432/farmu` | PostgreSQL 연결 URL (asyncpg 필수) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 캐시 |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery 브로커 |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery 결과 저장 |
| `JWT_SECRET_KEY` | *(변경 필수)* | JWT 서명 비밀키 — 프로덕션에서 반드시 교체 |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | 액세스 토큰 만료(분) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | 리프레시 토큰 만료(일) |
| `AWS_REGION` | `ap-northeast-2` | AWS 리전 |
| `AWS_ACCESS_KEY_ID` | *(선택)* | AWS 자격증명 |
| `AWS_SECRET_ACCESS_KEY` | *(선택)* | AWS 자격증명 |
| `S3_BUCKET_NAME` | `farmu-uploads` | S3 버킷 이름 |
| `S3_CDN_BASE_URL` | `https://cdn.farmu.kr` | CDN 베이스 URL |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | 허용 CORS 출처 (JSON 배열) |
| `SENTRY_DSN` | *(선택)* | Sentry 에러 트래킹 DSN |

**로컬 MinIO를 S3 대신 사용하려면** `.env`에 아래를 추가하세요:

```dotenv
AWS_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

---

## Makefile 커맨드

```bash
make help           # 전체 커맨드 목록 출력
```

| 커맨드 | 설명 |
|---|---|
| `make install` | Poetry 의존성 설치 |
| `make dev` | uvicorn 개발 서버 (hot-reload) |
| `make worker` | Celery 워커 실행 |
| `make lint` | ruff 코드 검사 |
| `make lint-fix` | ruff 자동 수정 |
| `make typecheck` | mypy 타입 체크 |
| `make test` | 전체 테스트 + 커버리지 |
| `make test-unit` | 단위 테스트 |
| `make test-integration` | 통합 테스트 |
| `make migrate` | `alembic upgrade head` |
| `make migrate-new msg="..."` | 마이그레이션 파일 자동 생성 |
| `make migrate-down` | 마이그레이션 1단계 롤백 |
| `make docker-up` | 로컬 인프라 컨테이너 시작 |
| `make docker-down` | 로컬 인프라 컨테이너 중지 |
| `make docker-reset` | 로컬 인프라 + 볼륨 초기화 |
| `make pre-commit-install` | pre-commit 훅 설치 |

---

## AWS 인프라

| 항목 | 서비스 |
|---|---|
| 컴퓨팅 | ECS Fargate |
| DB | RDS for PostgreSQL (PostGIS 확장) |
| 캐시/큐 | ElastiCache for Redis |
| 파일 스토리지 | S3 |
| 컨테이너 레지스트리 | ECR |
| 시크릿 관리 | Secrets Manager |
| 모니터링 | CloudWatch + Sentry |
| CDN/도메인 | CloudFront + Route 53 |
| CI/CD | GitHub Actions → ECR → ECS |
| 인스턴스 규모 | t3.medium (dev), t3.large (prod) |

배포 파이프라인: `main` 브랜치 푸시 → GitHub Actions → Docker 빌드 → ECR 푸시 → ECS 롤링 배포

---

## API 개요

- **Base URL**: `https://api.farmu.kr`
- **인증**: `Authorization: Bearer {accessToken}` (인증 API 제외)
- **Content-Type**: `application/json` (파일 업로드 시 `multipart/form-data`)

### 응답 형식

| 상황 | HTTP | 형식 |
|---|---|---|
| 단건 조회 | 200 | `{"data": {...}}` |
| 목록 조회 | 200 | `{"data": [...], "page": 0, "size": 20, "totalElements": N, ...}` |
| 생성 | 201 | 빈 응답 |
| 수정·삭제 | 204 | 빈 응답 |
| 비동기 작업 시작 | 202 | `{"data": {"jobId": "...", "status": "PROCESSING", "pollingUrl": "..."}}` |
| 에러 | 4xx / 5xx | RFC 9457 ProblemDetail (`application/problem+json`) |

### 주요 엔드포인트

| BC | 경로 |
|---|---|
| 인증 | `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `POST /api/v1/auth/users` |
| 대시보드 | `GET /api/v1/dashboard/summary` |
| 조합원 | `GET /api/v1/members/ranking` |
| 출하 추천 | `GET /api/v1/shipping/recommendations` |
| 필지/적합도 | `GET /api/v1/lands` |
| 시나리오 | `POST /api/v1/scenarios/simulate` |
| 멘토링 | `GET /api/v1/mentoring/suggestions` |
| 리포트 | `POST /api/v1/reports/generate` |
| 데이터 업로드 | `POST /api/v1/data/uploads` |

> 전체 API 명세는 개발 서버의 Swagger UI(`/docs`)에서 확인하세요. (`DEBUG=true` 설정 필요)

make docker-up    # 인프라 시작
make docker-down  # 인프라 종료
make migrate      # DB 마이그레이션
make dev          # 개발 서버 (hot-reload)
make lint         # 린트 검사
make test         # 테스트 실행