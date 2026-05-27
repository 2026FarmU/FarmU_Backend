"""Inbound port — Router가 호출하는 UseCase 인터페이스."""
from abc import ABC, abstractmethod

from src.auth.application.dto.commands import LoginCommand, RefreshTokenCommand
from src.auth.application.dto.results import LoginResult, TokenPair, UserInfo


class LoginUseCase(ABC):
    @abstractmethod
    async def login(self, command: LoginCommand) -> LoginResult: ...


class RefreshTokenUseCase(ABC):
    @abstractmethod
    async def refresh(self, command: RefreshTokenCommand) -> TokenPair: ...


class LogoutUseCase(ABC):
    @abstractmethod
    async def logout(self, user_id: str, access_token: str) -> None: ...


class GetCurrentUserUseCase(ABC):
    @abstractmethod
    async def get_me(self, user_id: str) -> UserInfo: ...
