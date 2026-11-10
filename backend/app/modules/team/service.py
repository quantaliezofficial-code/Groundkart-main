"""
Team management — the super admin's control over who else is an admin.

There is exactly one super admin (users.is_super_admin, enforced by a
partial unique index). They can add admins, suspend and reactivate them.
Regular admins cannot touch other admin accounts at all: not create, not
suspend, not reset a password. That last one matters — an admin able to
reset another admin's (or the super admin's) password would be able to
take the account over.
"""
from __future__ import annotations

import secrets
import uuid

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog, User
from app.modules.auth.security import hash_password


async def list_team(session: AsyncSession) -> list[dict]:
    """All admin accounts, super admin first, with a count of audited
    actions so the super admin can see who is actually doing what."""
    users = list(
        (
            await session.execute(
                select(User)
                .where(User.role == "admin", User.deleted_at.is_(None))
                .order_by(User.is_super_admin.desc(), User.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    if not users:
        return []
    ids = [u.id for u in users]
    activity = {
        r.actor_id: (int(r.actions), r.last_action_at)
        for r in (
            await session.execute(
                select(
                    AuditLog.actor_id,
                    func.count(AuditLog.id).label("actions"),
                    func.max(AuditLog.created_at).label("last_action_at"),
                )
                .where(AuditLog.actor_id.in_(ids))
                .group_by(AuditLog.actor_id)
            )
        ).all()
    }
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "phone": u.phone,
            "is_super_admin": u.is_super_admin,
            "suspended_at": u.suspended_at,
            "suspension_reason": u.suspension_reason,
            "created_at": u.created_at,
            "created_by": u.created_by,
            "action_count": activity.get(u.id, (0, None))[0],
            "last_action_at": activity.get(u.id, (0, None))[1],
        }
        for u in users
    ]


async def create_admin(
    session: AsyncSession, *, actor: User, name: str, phone: str, email: str | None
) -> User:
    """Super admin only (enforced by the route's dependency AND here, so the
    rule holds for any future caller). The new account gets an unusable
    random password; the route then issues a one-time set-password link."""
    if not actor.is_super_admin:
        raise HTTPException(status_code=403, detail="Only the super admin can add admins")
    try:
        async with session.begin():
            conditions = [User.phone == phone]
            if email:
                conditions.append(User.email == email)
            if (await session.execute(select(User).where(or_(*conditions)))).scalars().first() is not None:
                raise HTTPException(
                    status_code=409, detail="An account with this phone or email already exists"
                )
            user = User(
                name=name,
                email=email,
                phone=phone,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                role="admin",
                is_verified=True,
                is_super_admin=False,
                must_change_password=True,
                created_by=actor.id,
            )
            session.add(user)
            await session.flush()
            session.add(
                AuditLog(
                    actor_id=actor.id,
                    action="team.admin_created",
                    entity_type="user",
                    entity_id=user.id,
                    extra_data={"name": name},
                )
            )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="An account with this phone or email already exists")
    return user


async def assert_can_manage_account(session: AsyncSession, actor_id: uuid.UUID, target_id: uuid.UUID) -> None:
    """Shared guard for suspend / reactivate / password reset.

    * Nobody can act on the super admin's account through these routes.
    * Only the super admin can act on another admin's account.
    Customers, owners and brokers remain manageable by any admin.

    Reads on its own session so it never leaves a transaction open on the
    caller's."""
    from app.db import SessionLocal

    async with SessionLocal() as own:
        rows = {
            u.id: u
            for u in (
                await own.execute(select(User).where(User.id.in_([actor_id, target_id])))
            ).scalars()
        }
    target = rows.get(target_id)
    actor = rows.get(actor_id)
    if target is None or actor is None:
        return  # the service being guarded produces its own 404
    if actor_id == target_id:
        return  # self-service; each caller has its own rule for that
    if target.is_super_admin:
        raise HTTPException(status_code=403, detail="The super admin account can't be changed from here")
    if target.role == "admin" and not actor.is_super_admin:
        raise HTTPException(status_code=403, detail="Only the super admin can manage admin accounts")
