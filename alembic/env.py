import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.account_models import (  # noqa: F401
    NotificationSettingOrmModel,
    UnionWeightOrmModel,
    UserMemberLinkOrmModel,
    UserProfileOrmModel,
)
from src.alert.adapter.persistence.model.alert_model import AlertOrmModel  # noqa: F401
from src.auth.adapter.persistence.model.union_model import UnionOrmModel  # noqa: F401

# BC별 ORM 모델 임포트 (마이그레이션 autogenerate 감지용)
from src.auth.adapter.persistence.model.user_model import UserOrmModel  # noqa: F401
from src.data_ingest.adapter.persistence.model.upload_model import DataUploadOrmModel  # noqa: F401
from src.infrastructure.database.session import Base
from src.land.adapter.persistence.model.land_model import (  # noqa: F401
    LandOrmModel,
    LandSuitabilityOrmModel,
)
from src.main.config import get_settings
from src.mentoring.adapter.persistence.model.mentoring_model import (
    MentoringMatchOrmModel,  # noqa: F401
)
from src.notification.adapter.persistence.model.notification_model import (
    NotificationOrmModel,  # noqa: F401
)
from src.report.adapter.persistence.model.report_model import ReportOrmModel  # noqa: F401
from src.scenario.adapter.persistence.model.scenario_model import ScenarioOrmModel  # noqa: F401

config = context.config
settings = get_settings()

# .env DATABASE_URL 우선 적용
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
