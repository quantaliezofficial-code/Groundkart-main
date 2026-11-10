"""
Admin Setup Script
Creates or updates an administrator account from environment variables:
- ADMIN_EMAIL (required)
- ADMIN_PHONE (required)
- ADMIN_PASSWORD (optional: if omitted, generates a 16-byte URL-safe token, prints it once, and flags must_change_password=True)
- ADMIN_NAME (optional display name)
- ADMIN_SUPER (optional: "transfer" moves the super admin role to this account even if another account holds it)

Super admin: there is exactly one. If no account holds the role yet, the account
this script creates or updates becomes the super admin. If another account already
holds it, this account is a regular admin unless ADMIN_SUPER=transfer is set.
Uses the application's configured settings.database_url — never a hardcoded connection string.
"""
import asyncio
import os
import secrets
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.models.core import User
from app.modules.auth.security import hash_password


async def setup_admin() -> None:
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
    admin_phone = os.environ.get("ADMIN_PHONE", "").strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()

    if not admin_email or not admin_phone:
        sys.exit(
            "ERROR: Missing required environment variables.\n"
            "Both ADMIN_EMAIL and ADMIN_PHONE must be provided to run admin_setup.py."
        )

    must_change = False
    if not admin_password:
        admin_password = secrets.token_urlsafe(16)
        must_change = True
        print(f"Generated temporary admin password: {admin_password}")
        print("Note: must_change_password has been set to True for this account.")
    else:
        print("Using provided ADMIN_PASSWORD.")

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.email == admin_email))
            admin = result.scalar_one_or_none()

            holder = (
                await session.execute(
                    select(User).where(User.is_super_admin.is_(True)).with_for_update()
                )
            ).scalar_one_or_none()
            transfer = os.environ.get("ADMIN_SUPER", "").strip().lower() == "transfer"
            make_super = holder is None or (admin is not None and holder.id == admin.id) or transfer
            if transfer and holder is not None and (admin is None or holder.id != admin.id):
                holder.is_super_admin = False
                await session.flush()  # release the single-super-admin slot first
                print(f"Super admin role removed from: {holder.email or holder.phone}")

            if admin:
                admin.phone = admin_phone
                admin.password_hash = hash_password(admin_password)
                admin.role = "admin"
                admin.is_verified = True
                admin.must_change_password = must_change
                admin.suspended_at = None
                admin.suspension_reason = None
                admin.is_super_admin = make_super
                print(f"Admin account updated: {admin_email} (role: {'super admin' if make_super else 'admin'})")
            else:
                admin = User(
                    name=os.environ.get("ADMIN_NAME", "").strip() or "Admin",
                    is_super_admin=make_super,
                    email=admin_email,
                    phone=admin_phone,
                    password_hash=hash_password(admin_password),
                    role="admin",
                    is_verified=True,
                    must_change_password=must_change,
                )
                session.add(admin)
                print(f"Admin account created: {admin_email} (role: {'super admin' if make_super else 'admin'})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(setup_admin())
