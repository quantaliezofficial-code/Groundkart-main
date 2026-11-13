"""DEMO DATA guard (compliance brief ground rule 2).

Seed scripts mark what they create with is_demo=true. GET /api/v1/meta/demo
lets the frontend show a "DEMO DATA" banner, and the API refuses to start
in production while any demo row exists, so sample reviews and fake venues
can never be served to real customers."""
from __future__ import annotations

from sqlalchemy import func, select

from app.models.core import Review, User, Venue


async def demo_counts(session) -> dict[str, int]:
    counts = {}
    for name, model in (("users", User), ("venues", Venue), ("reviews", Review)):
        counts[name] = (await session.execute(select(func.count()).select_from(model).where(model.is_demo.is_(True)))).scalar_one()
    return counts


async def assert_no_demo_data_in_production(session_factory, environment: str) -> None:
    if environment.lower() not in ("prod", "production"):
        return
    async with session_factory() as session:
        counts = await demo_counts(session)
    if any(counts.values()):
        raise RuntimeError(
            f"DEMO DATA present in a production database ({counts}). "
            "Remove it with `python -m scripts.purge_demo_data --yes` before starting."
        )


# Passwords that appear in this repository's dev seed scripts and e2e
# fixtures. A production admin must never use one of them.
KNOWN_DEV_PASSWORDS = ("Admin@2026!", "Demo@2026!", "admin123", "password123")


async def assert_no_known_dev_passwords_in_production(session_factory, environment: str) -> None:
    if environment.lower() not in ("prod", "production"):
        return
    from app.modules.auth.security import verify_password

    async with session_factory() as session:
        admins = (await session.execute(select(User).where(User.role == "admin", User.deleted_at.is_(None)))).scalars().all()
    weak = [a.email or a.phone for a in admins if any(verify_password(p, a.password_hash) for p in KNOWN_DEV_PASSWORDS)]
    if weak:
        raise RuntimeError(
            f"Admin account(s) {weak} use a password published in this repository's dev scripts. "
            "Reset them with `python -m scripts.admin_setup` before starting in production."
        )
