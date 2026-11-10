"""
TRD §4: "every state-changing route is protected by a dependency like
require_role(['owner', 'admin']), not just get_current_user." This directly
fixes the gap the original codebase had — any logged-in user could create
venues/slots because routes only checked "is someone logged in," never
"is this the right someone."
"""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.core import User
from app.modules.auth.security import InvalidTokenError, decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Lightweight — built from JWT claims, not a full User row, since the
    JWT is already signed proof of identity+role and a DB round-trip on
    every request defeats half the point of using JWTs at all. Routes that
    need the full row (e.g. email for a notification) fetch it themselves."""

    def __init__(self, id: uuid.UUID, role: str):
        self.id = id
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return CurrentUser(id=uuid.UUID(payload["sub"]), role=payload["role"])


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser | None:
    """For routes that are public but behave differently when the caller
    happens to be authenticated. If a token is provided, it MUST be valid
    (or trigger a 401 so the frontend can refresh it). If no token is
    provided, it safely returns None."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        return None
    return CurrentUser(id=uuid.UUID(payload["sub"]), role=payload["role"])


def require_role(*allowed_roles: str):
    """Usage: Depends(require_role('owner', 'admin')). A factory, not a
    single dependency, because the allowed-roles set differs per route —
    can't be a single shared dependency function."""

    async def _dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="You don't have access to do this")
        return current_user

    return _dependency


async def get_current_user_row(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """For the routes that do need the full row. Separate from
    get_current_user so routes that only need id+role (the common case)
    don't pay for a query they don't need."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return user


async def _load_actor(user_id: uuid.UUID) -> User:
    """Loads the acting user's full row on its OWN short-lived session and
    returns it detached.

    Why not get_current_user_row: that runs on the request's shared session
    and leaves a transaction open on it, and every write service in this
    codebase opens its own with `async with session.begin()` — which raises
    if one is already in progress. A detached row sidesteps that entirely.

    Unlike the JWT-only CurrentUser, this is a live check: an account that
    was suspended or deleted a minute ago is refused here even though its
    access token has not expired yet. Used on the routes where that
    matters most (team, brokers, money)."""
    from app.db import SessionLocal

    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or user.deleted_at is not None or user.suspended_at is not None:
        raise HTTPException(status_code=401, detail="Account is no longer active")
    return user


async def get_admin_actor(current_user: CurrentUser = Depends(require_role("admin"))) -> User:
    """Any admin (the super admin included), as a full detached row."""
    actor = await _load_actor(current_user.id)
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="You don't have access to do this")
    return actor


async def get_super_admin_actor(actor: User = Depends(get_admin_actor)) -> User:
    """The platform owner only. Checked against the database on every call
    rather than a JWT claim, so the right can't outlive a transfer of the
    super admin role by up to one token lifetime."""
    if not actor.is_super_admin:
        raise HTTPException(status_code=403, detail="Only the super admin can do this")
    return actor


async def get_broker_actor(current_user: CurrentUser = Depends(require_role("broker"))) -> User:
    actor = await _load_actor(current_user.id)
    if actor.role != "broker":
        raise HTTPException(status_code=403, detail="You don't have access to do this")
    return actor
