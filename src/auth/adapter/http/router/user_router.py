"""프론트엔드 프로필 화면용 사용자 API."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account_models import (
    NotificationSettingOrmModel,
    UserMemberLinkOrmModel,
    UserProfileOrmModel,
)
from src.auth.adapter.http.router.deps import AuthServiceDep, CurrentUser
from src.auth.adapter.http.schema.auth_schema import (
    ChangePasswordRequest,
    MeResponse,
    UpdateProfileRequest,
)
from src.infrastructure.database.session import get_db_session
from src.main.config import get_settings
from src.main.response_schema import DataResponse, ListResponse

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class NotificationSettingItem(BaseModel):
    key: str
    channels: list[Literal["PUSH", "EMAIL"]]
    enabled: bool


class NotificationSettingsRequest(BaseModel):
    settings: list[NotificationSettingItem]


class MemberLinkRequest(BaseModel):
    memberId: str


class ProfileResponse(MeResponse):
    memberId: str | None = None
    phone: str | None = None
    email: str | None = None
    bio: str | None = None
    avatarUrl: str | None = None
    bannerUrl: str | None = None


class ImageResponse(BaseModel):
    avatarUrl: str | None
    bannerUrl: str | None


@router.get(
    "/me", status_code=status.HTTP_200_OK, response_model=DataResponse[ProfileResponse]
)
async def get_my_profile(
    current: CurrentUser,
    svc: AuthServiceDep,
    session: DbSession,
) -> ORJSONResponse:
    info = await svc.get_me(current.user_id)
    profile = await session.get(UserProfileOrmModel, current.user_id)
    link = await session.get(UserMemberLinkOrmModel, current.user_id)
    return ORJSONResponse(
        {
            "data": {
                **MeResponse(
                    userId=info.user_id,
                    name=info.name,
                    role=info.role.value,
                    unionId=info.union_id,
                    permissions=info.permissions,
                ).model_dump(),
                "memberId": link.member_id if link else None,
                "phone": profile.phone if profile else None,
                "email": profile.email if profile else None,
                "bio": profile.bio if profile else None,
                "avatarUrl": profile.avatar_url if profile else None,
                "bannerUrl": profile.banner_url if profile else None,
            }
        }
    )


@router.patch(
    "/me", status_code=status.HTTP_200_OK, response_model=DataResponse[MeResponse]
)
async def update_my_profile(
    body: UpdateProfileRequest,
    current: CurrentUser,
    svc: AuthServiceDep,
    session: DbSession,
) -> ORJSONResponse:
    current_info = await svc.get_me(current.user_id)
    info = await svc.update_profile(current.user_id, body.name or current_info.name)
    profile = await session.get(UserProfileOrmModel, current.user_id)
    if profile is None:
        profile = UserProfileOrmModel(user_id=current.user_id)
        session.add(profile)
    if body.phone is not None:
        profile.phone = body.phone
    if body.email is not None:
        profile.email = body.email
    if body.bio is not None:
        profile.bio = body.bio
    await session.commit()
    return ORJSONResponse(
        {
            "data": MeResponse(
                userId=info.user_id,
                name=info.name,
                role=info.role.value,
                unionId=info.union_id,
                permissions=info.permissions,
            ).model_dump()
        }
    )


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    body: ChangePasswordRequest,
    current: CurrentUser,
    svc: AuthServiceDep,
) -> None:
    await svc.change_password(
        current.user_id,
        body.currentPassword,
        body.newPassword,
    )


@router.patch(
    "/me/images", status_code=status.HTTP_200_OK, response_model=DataResponse[ImageResponse]
)
async def update_my_images(
    current: CurrentUser,
    session: DbSession,
    avatar: UploadFile | None = File(default=None),
    banner: UploadFile | None = File(default=None),
) -> ORJSONResponse:
    if avatar is None and banner is None:
        raise HTTPException(status_code=400, detail="avatar 또는 banner 파일이 필요합니다.")
    profile = await session.get(UserProfileOrmModel, current.user_id)
    if profile is None:
        profile = UserProfileOrmModel(user_id=current.user_id)
        session.add(profile)
    base = get_settings().s3_cdn_base_url.rstrip("/")
    for kind, file in (("avatar", avatar), ("banner", banner)):
        if file is None:
            continue
        if not (file.content_type or "").startswith("image/"):
            raise HTTPException(status_code=415, detail="이미지 파일만 지원합니다.")
        content = await file.read(5 * 1024 * 1024 + 1)
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="이미지는 최대 5MB입니다.")
        url = f"{base}/{kind}/{current.user_id}"
        if kind == "avatar":
            profile.avatar_url = url
        else:
            profile.banner_url = url
    await session.commit()
    return ORJSONResponse(
        {"data": {"avatarUrl": profile.avatar_url, "bannerUrl": profile.banner_url}}
    )


@router.get(
    "/me/notifications",
    status_code=status.HTTP_200_OK,
    response_model=ListResponse[NotificationSettingItem],
)
async def get_notification_settings(current: CurrentUser, session: DbSession) -> ORJSONResponse:
    rows = list(
        (
            await session.scalars(
                select(NotificationSettingOrmModel).where(
                    NotificationSettingOrmModel.user_id == current.user_id
                )
            )
        ).all()
    )
    if not rows:
        defaults = [
            ("RISK_ALERT", "PUSH,EMAIL", True),
            ("SCENARIO_DONE", "PUSH", True),
            ("REPORT_DONE", "PUSH,EMAIL", True),
        ]
        rows = [
            NotificationSettingOrmModel(
                user_id=current.user_id, key=key, channels=channels, enabled=enabled
            )
            for key, channels, enabled in defaults
        ]
        session.add_all(rows)
        await session.commit()
    return ORJSONResponse(
        {
            "data": [
                {
                    "key": r.key,
                    "channels": r.channels.split(",") if r.channels else [],
                    "enabled": r.enabled,
                }
                for r in rows
            ]
        }
    )


@router.put("/me/notifications", status_code=status.HTTP_204_NO_CONTENT)
async def update_notification_settings(
    body: NotificationSettingsRequest, current: CurrentUser, session: DbSession
) -> None:
    await session.execute(
        delete(NotificationSettingOrmModel).where(
            NotificationSettingOrmModel.user_id == current.user_id
        )
    )
    session.add_all(
        [
            NotificationSettingOrmModel(
                user_id=current.user_id,
                key=item.key,
                channels=",".join(item.channels),
                enabled=item.enabled,
            )
            for item in body.settings
        ]
    )
    await session.commit()


@router.put("/{user_id}/member", status_code=status.HTTP_204_NO_CONTENT)
async def link_user_member(
    user_id: str, body: MemberLinkRequest, current: CurrentUser, session: DbSession
) -> None:
    if current.role != "UNION_ADMIN":
        raise HTTPException(status_code=403, detail="UNION_ADMIN 권한이 필요합니다.")
    await session.merge(UserMemberLinkOrmModel(user_id=user_id, member_id=body.memberId))
    await session.commit()
