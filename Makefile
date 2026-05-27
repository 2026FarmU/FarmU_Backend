.PHONY: help install dev lint test migrate docker-up docker-down

PYTHON := python3.12
POETRY := $(HOME)/.local/bin/poetry

help: ## 도움말
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 의존성 설치
	$(POETRY) install

dev: ## 개발 서버 실행
	$(POETRY) run uvicorn src.main.app:app --reload --host 0.0.0.0 --port 8000

worker: ## Celery 워커 실행
	$(POETRY) run celery -A src.infrastructure.celery.app worker --loglevel=info

lint: ## 코드 린트
	$(POETRY) run ruff check src tests
	$(POETRY) run ruff format --check src tests

lint-fix: ## 린트 자동 수정
	$(POETRY) run ruff check --fix src tests
	$(POETRY) run ruff format src tests

typecheck: ## 타입 체크
	$(POETRY) run mypy src

test: ## 테스트 실행
	$(POETRY) run pytest

test-unit: ## 단위 테스트만 실행
	$(POETRY) run pytest tests/unit -v

test-integration: ## 통합 테스트만 실행
	$(POETRY) run pytest tests/integration -v

migrate: ## DB 마이그레이션 실행
	$(POETRY) run alembic upgrade head

migrate-new: ## 새 마이그레이션 생성 (make migrate-new msg="add user table")
	$(POETRY) run alembic revision --autogenerate -m "$(msg)"

migrate-down: ## 마이그레이션 롤백
	$(POETRY) run alembic downgrade -1

docker-up: ## 로컬 인프라 시작 (PostgreSQL, Redis, MinIO)
	docker compose up -d
	@echo "⏳ 서비스 준비 대기..."
	@sleep 3
	@echo "✅ PostgreSQL: localhost:5432"
	@echo "✅ Redis:      localhost:6379"
	@echo "✅ MinIO:      localhost:9000 (콘솔: localhost:9001)"

docker-down: ## 로컬 인프라 중지
	docker compose down

docker-reset: ## 로컬 인프라 초기화 (볼륨 삭제)
	docker compose down -v

pre-commit-install: ## pre-commit 훅 설치
	$(POETRY) run pre-commit install
