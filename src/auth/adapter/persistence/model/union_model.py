"""Union ORM 모델 (auth BC용 읽기 전용 최소 정의).

Union BC가 구현되면 해당 BC의 모델을 사용하거나
UnionQueryPort 구현체를 교체하면 됩니다.
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class UnionOrmModel(Base):
    __tablename__ = "unions"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    def __repr__(self) -> str:
        return f"<Union id={self.id} code={self.code}>"
