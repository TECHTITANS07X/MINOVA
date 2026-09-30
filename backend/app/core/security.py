from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

_jwks_cache: dict | None = None


class TokenUser(BaseModel):
    sub: str
    email: str = ""
    name: str = ""
    roles: list[str] = []
    mine_id: str | None = None
    department: str | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.effective_jwks_url, timeout=10)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


def _extract_roles(payload: dict) -> list[str]:
    roles: list[str] = []
    realm_access = payload.get("realm_access", {})
    roles.extend(realm_access.get("roles", []))
    resource_access = payload.get("resource_access", {})
    for client_roles in resource_access.values():
        roles.extend(client_roles.get("roles", []))
    return list(set(roles))


async def get_current_user(request: Request) -> TokenUser:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = auth_header[7:]
    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = k
                break
        if key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
            options={"verify_aud": False},
        )
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

    return TokenUser(
        sub=payload.get("sub", ""),
        email=payload.get("email", ""),
        name=payload.get("preferred_username", payload.get("name", "")),
        roles=_extract_roles(payload),
        mine_id=payload.get("mine"),
        department=payload.get("department"),
    )


CurrentUser = Annotated[TokenUser, Depends(get_current_user)]


def require_role(*allowed_roles: str):
    async def _check(user: CurrentUser) -> TokenUser:
        if not any(r in user.roles for r in allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user
    return Depends(_check)


def require_mine_access(mine_id_param: str = "mine_id"):
    async def _check(request: Request, user: CurrentUser) -> TokenUser:
        if "admin" in user.roles or "corporate_viewer" in user.roles:
            return user
        requested_mine = request.path_params.get(mine_id_param)
        if requested_mine and user.mine_id and requested_mine != user.mine_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this mine")
        return user
    return Depends(_check)
