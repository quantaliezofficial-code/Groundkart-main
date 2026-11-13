"""Shared helpers for the @compliance test suite (tests/test_compliance_*.py).

Each compliance test file maps to one group of the Rinisha checklist (see
docs/compliance/source_checklist.md for item IDs). Test names start with the
item ID, e.g. test_1_2_notice_lists_data_types, so docs/compliance/score.py
can attribute results to checklist items.
"""
from __future__ import annotations

import pathlib
import uuid
from datetime import date, time, timedelta

import httpx
import pytest
from sqlalchemy import select

from app.db import get_db, get_idem_db
from app.main import app
from app.models.core import Booking, InventoryUnit, User, Venue
from app.modules.auth.security import create_access_token, hash_password

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LEGAL_DIR = REPO_ROOT / "frontend" / "src" / "content" / "legal"
DRAFTS_DIR = REPO_ROOT / "docs" / "compliance" / "drafts"

PASSWORD = "Strong-Passw0rd!"


@pytest.fixture
async def client(test_session_factory):
    async def _override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_idem_db] = _override_get_db
    transport = httpx.ASGITransport(app=app, client=("203.0.113.7", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def auth(user_id: uuid.UUID, role: str, amr: list[str] | None = None) -> dict:
    token = create_access_token(user_id, role, amr=amr) if amr is not None else create_access_token(user_id, role)
    return {"Authorization": f"Bearer {token}"}


async def make_user(factory, role: str = "customer", *, super_admin: bool = False, verified: bool = False, name: str = "Test Person") -> User:
    async with factory() as session:
        async with session.begin():
            user = User(
                name=name,
                email=f"{role}-{uuid.uuid4().hex[:8]}@example.com",
                phone=f"9{uuid.uuid4().int % 10**9:09d}",
                password_hash=hash_password(PASSWORD),
                role=role,
                is_super_admin=super_admin,
                is_verified=verified,
            )
            session.add(user)
            await session.flush()
        return user


async def make_venue_with_unit(factory, owner_id: uuid.UUID, *, days_ahead: int = 30) -> tuple[uuid.UUID, uuid.UUID]:
    async with factory() as session:
        async with session.begin():
            venue = Venue(
                owner_id=owner_id,
                name="Compliance Test Turf",
                slug=f"compliance-turf-{uuid.uuid4().hex[:8]}",
                category="sports",
                address="1 Test Road",
                city="Lucknow",
                unit_type="hour",
                base_price=1500,
                status="active",
            )
            session.add(venue)
            await session.flush()
            unit = InventoryUnit(
                venue_id=venue.id,
                date=date.today() + timedelta(days=days_ahead),
                start_time=time(18, 0),
                end_time=time(19, 0),
                price=1500,
                status="available",
            )
            session.add(unit)
            await session.flush()
            return venue.id, unit.id


async def make_unit(factory, venue_id: uuid.UUID, *, days_ahead: int = 31, hour: int = 7) -> uuid.UUID:
    async with factory() as session:
        async with session.begin():
            unit = InventoryUnit(
                venue_id=venue_id,
                date=date.today() + timedelta(days=days_ahead),
                start_time=time(hour, 0),
                end_time=time(hour + 1, 0),
                price=1500,
                status="available",
            )
            session.add(unit)
            await session.flush()
            return unit.id


async def make_booking(factory, venue_id: uuid.UUID, unit_id: uuid.UUID, customer_id: uuid.UUID | None, status: str = "completed", **guest) -> uuid.UUID:
    async with factory() as session:
        async with session.begin():
            booking = Booking(
                customer_id=customer_id,
                venue_id=venue_id,
                venue_name="Compliance Test Turf",
                venue_category="sports",
                inventory_unit_id=unit_id,
                status=status,
                amount=1500,
                currency="INR",
                **guest,
            )
            session.add(booking)
            await session.flush()
            return booking.id


async def fetch(factory, model, **where):
    async with factory() as session:
        stmt = select(model)
        for k, v in where.items():
            stmt = stmt.where(getattr(model, k) == v)
        return (await session.execute(stmt)).scalars().all()


def signup_body(**over) -> dict:
    body = {
        "name": "Asha Verma",
        "email": f"asha-{uuid.uuid4().hex[:6]}@example.com",
        "phone": f"98{uuid.uuid4().int % 10**8:08d}",
        "password": PASSWORD,
        "age_confirmed": True,
    }
    body.update(over)
    return body


def legal(name: str) -> str:
    return (LEGAL_DIR / name).read_text(encoding="utf-8")
