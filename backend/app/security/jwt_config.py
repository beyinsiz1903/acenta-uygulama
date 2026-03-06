from __future__ import annotations

from app.config import require_env


JWT_ALGORITHM = "HS256"


def get_jwt_secret() -> str:
    return require_env("JWT_SECRET")


def require_jwt_secret() -> None:
    get_jwt_secret()
