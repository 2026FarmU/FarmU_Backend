"""bcrypt 비밀번호 해셔 (passlib 없이 bcrypt 직접 사용)."""
import bcrypt

from src.auth.application.port.required.password_hasher import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, plain_password: str) -> str:
        return bcrypt.hashpw(
            plain_password.encode(), bcrypt.gensalt(rounds=12)
        ).decode()

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
