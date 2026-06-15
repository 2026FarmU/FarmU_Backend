"""헤더 알림 패널 API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.adapter.http.router.deps import CurrentUser
from src.infrastructure.database.session import get_db_session
from src.main.response_schema import DataResponse, ListResponse
from src.notification.adapter.persistence.model.notification_model import NotificationOrmModel
from src.shared.domain.exception import EntityNotFoundException

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class UnreadCountResponse(BaseModel):
    unreadCount: int


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    message: str
    level: str
    isRead: bool
    actionUrl: str | None
    createdAt: str


@router.get(
    "/unread-count",
    status_code=status.HTTP_200_OK,
    response_model=DataResponse[UnreadCountResponse],
)
async def get_unread_count(current: CurrentUser, session: DbSession) -> ORJSONResponse:
    count = await session.scalar(
        select(func.count(NotificationOrmModel.id)).where(
            NotificationOrmModel.user_id == current.user_id, NotificationOrmModel.is_read.is_(False)
        )
    )
    return ORJSONResponse({"data": {"unreadCount": count or 0}})


@router.get("", status_code=status.HTTP_200_OK, response_model=ListResponse[NotificationItem])
async def get_notifications(
    current: CurrentUser, session: DbSession, size: int = Query(default=10, ge=1, le=100)
) -> ORJSONResponse:
    rows = list(
        (
            await session.scalars(
                select(NotificationOrmModel)
                .where(NotificationOrmModel.user_id == current.user_id)
                .order_by(NotificationOrmModel.created_at.desc())
                .limit(size)
            )
        ).all()
    )
    return ORJSONResponse(
        {
            "data": [
                {
                    "id": r.id,
                    "type": r.type,
                    "title": r.title,
                    "message": r.message,
                    "level": r.level,
                    "isRead": r.is_read,
                    "actionUrl": r.action_url,
                    "createdAt": r.created_at,
                }
                for r in rows
            ]
        }
    )


@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all_notifications(current: CurrentUser, session: DbSession) -> None:
    await session.execute(
        update(NotificationOrmModel)
        .where(
            NotificationOrmModel.user_id == current.user_id, NotificationOrmModel.is_read.is_(False)
        )
        .values(is_read=True)
    )
    await session.commit()


@router.patch("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_notification(notification_id: str, current: CurrentUser, session: DbSession) -> None:
    row = await session.get(NotificationOrmModel, notification_id)
    if row is None or row.user_id != current.user_id:
        raise EntityNotFoundException("Notification", notification_id)
    row.is_read = True
    await session.commit()
