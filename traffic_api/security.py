from __future__ import annotations

from typing import Callable

from traffic_api.config import AppSettings


def api_key_dependency(settings: AppSettings) -> Callable:
    from fastapi import Header, HTTPException, status

    async def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        if settings.api_key and x_api_key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "unauthorized", "message": "Invalid or missing X-API-Key."},
            )

    return verify_api_key

