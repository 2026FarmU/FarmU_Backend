"""Auth 유스케이스 구현체."""
from src.auth.application.dto.commands import (
    CreateUserCommand,
    LoginCommand,
    RefreshTokenCommand,
    RegisterCommand,
)
from src.auth.application.dto.results import (
    LoginResult,
    RegisterResult,
    TokenPair,
    UserInfo,
)
from src.auth.application.port.provided.auth_use_case import (
    CreateUserUseCase,
    GetCurrentUserUseCase,
    LoginUseCase,
    LogoutUseCase,
    RegisterUseCase,
    RefreshTokenUseCase,
)
from src.auth.application.port.required.jwt_service import JwtService, TokenPayload
from src.auth.application.port.required.password_hasher import PasswordHasher
from src.auth.application.port.required.token_store import TokenStore
from src.auth.application.port.required.union_query_port import UnionQueryPort
from src.auth.domain.exception import (
    DuplicateLoginIdException,
    InvalidCredentialsException,
    UnionNotFoundException,
)
from src.auth.domain.model.role import Role
from src.auth.domain.model.user import User
from src.auth.domain.repository.user_repository import UserRepository
from src.auth.domain.model.vo import LoginId, UnionId, UserId
from src.shared.domain.exception import DomainException, EntityNotFoundException


class AuthService(
    RegisterUseCase,
    CreateUserUseCase,
    LoginUseCase,
    RefreshTokenUseCase,
    LogoutUseCase,
    GetCurrentUserUseCase,
):
    def __init__(
        self,
        user_repo: UserRepository,
        union_query: UnionQueryPort,
        password_hasher: PasswordHasher,
        jwt_service: JwtService,
        token_store: TokenStore,
    ) -> None:
        self._user_repo = user_repo
        self._union_query = union_query
        self._password_hasher = password_hasher
        self._jwt_service = jwt_service
        self._token_store = token_store

    # ── RegisterUseCase ───────────────────────────────────────────

    async def register(self, command: RegisterCommand) -> RegisterResult:
        union_id = await self._union_query.find_id_by_code(command.union_code)
        if union_id is None:
            raise UnionNotFoundException(command.union_code)

        login_id = LoginId(command.login_id)
        domain_union_id = UnionId(union_id)
        if await self._user_repo.exists_by_login_id_and_union(login_id, domain_union_id):
            raise DuplicateLoginIdException(command.login_id)

        user = User(
            id=UserId.generate(),
            login_id=login_id,
            hashed_password=self._password_hasher.hash(command.password),
            name=command.name,
            role=Role.UNION_ADMIN,
            union_id=domain_union_id,
        )
        saved = await self._user_repo.save(user)
        return RegisterResult(user_id=str(saved.id))

    async def create_user(self, command: CreateUserCommand) -> RegisterResult:
        login_id = LoginId(command.login_id)
        domain_union_id = UnionId(command.union_id)
        if await self._user_repo.exists_by_login_id_and_union(login_id, domain_union_id):
            raise DuplicateLoginIdException(command.login_id)

        try:
            role = Role(command.role)
        except ValueError as exc:
            raise DomainException(
                message=f"지원하지 않는 role 입니다: {command.role}",
                code="INVALID_ROLE",
            ) from exc

        if role not in (Role.MEMBER, Role.UNION_ADMIN):
            raise DomainException(
                message="관리자 생성에서는 MEMBER 또는 UNION_ADMIN만 허용됩니다.",
                code="INVALID_ROLE",
            )

        user = User(
            id=UserId.generate(),
            login_id=login_id,
            hashed_password=self._password_hasher.hash(command.password),
            name=command.name,
            role=role,
            union_id=domain_union_id,
        )
        saved = await self._user_repo.save(user)
        return RegisterResult(user_id=str(saved.id))

    # ── LoginUseCase ──────────────────────────────────────────────

    async def login(self, command: LoginCommand) -> LoginResult:
        # 1) 조합 코드 → ID 조회
        union_id = await self._union_query.find_id_by_code(command.union_code)
        if union_id is None:
            raise UnionNotFoundException(command.union_code)

        # 2) 사용자 조회
        user = await self._user_repo.find_by_login_id_and_union(
            LoginId(command.login_id), UnionId(union_id)
        )
        if user is None:
            raise InvalidCredentialsException()

        # 3) 탈퇴 여부 확인
        user.verify_not_withdrawn()

        # 4) 비밀번호 검증
        if not self._password_hasher.verify(command.password, user.hashed_password):
            raise InvalidCredentialsException()

        # 5) 토큰 발급
        payload = TokenPayload(
            user_id=str(user.id),
            role=user.role.value,
            union_id=str(user.union_id),
        )
        access_token, expires_in = self._jwt_service.create_access_token(payload)
        refresh_token = self._jwt_service.create_refresh_token(payload)

        # 6) 리프레시 토큰 저장 (30일)
        await self._token_store.save_refresh_token(
            str(user.id), refresh_token, ttl_seconds=30 * 24 * 3600
        )

        return LoginResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user=UserInfo(
                user_id=str(user.id),
                name=user.name,
                role=user.role,
                union_id=str(user.union_id),
                permissions=user.permissions,
            ),
        )

    # ── RefreshTokenUseCase ───────────────────────────────────────

    async def refresh(self, command: RefreshTokenCommand) -> TokenPair:
        # 1) 리프레시 토큰 검증 (만료·변조 → JwtService에서 예외)
        payload = self._jwt_service.decode_refresh_token(command.refresh_token)

        # 2) 저장된 토큰과 일치하는지 확인
        stored = await self._token_store.get_refresh_token(payload.user_id)
        if stored != command.refresh_token:
            from src.shared.domain.exception import DomainException
            raise DomainException(
                message="유효하지 않은 리프레시 토큰입니다.",
                code="INVALID_REFRESH_TOKEN",
            )

        # 3) 새 토큰 발급
        access_token, _ = self._jwt_service.create_access_token(payload)
        new_refresh = self._jwt_service.create_refresh_token(payload)

        await self._token_store.save_refresh_token(
            payload.user_id, new_refresh, ttl_seconds=30 * 24 * 3600
        )

        return TokenPair(access_token=access_token, refresh_token=new_refresh)

    # ── LogoutUseCase ─────────────────────────────────────────────

    async def logout(self, user_id: str, access_token: str) -> None:
        # 리프레시 토큰 삭제 + 액세스 토큰 블랙리스트 등록 (1시간)
        await self._token_store.delete_refresh_token(user_id)
        await self._token_store.blacklist_access_token(
            access_token, ttl_seconds=3600
        )

    # ── GetCurrentUserUseCase ─────────────────────────────────────

    async def get_me(self, user_id: str) -> UserInfo:
        user = await self._user_repo.find_by_id(UserId(user_id))
        if user is None:
            raise EntityNotFoundException("User", user_id)
        user.verify_not_withdrawn()
        return UserInfo(
            user_id=str(user.id),
            name=user.name,
            role=user.role,
            union_id=str(user.union_id),
            permissions=user.permissions,
        )
