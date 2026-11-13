"""
Site banners — promotional slots an admin controls without a deploy.

Several banners can be live in the same placement at once; the site
rotates through them in priority order. Each can be scheduled, so a
festive-season banner can be prepared ahead and take itself down.

Placements:
  home_hero   large slides at the top of the homepage
  home_strip  a slim announcement strip under the homepage hero
  search_top  a strip above search results
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog, SiteBanner

PLACEMENTS = ("home_hero", "home_strip", "search_top")
MAX_LIVE_PER_PLACEMENT = 8


def clean_cta_url(raw: str | None) -> str | None:
    """A banner link is admin-supplied and rendered as an href for every
    visitor, so it is restricted to what is safe to click: a path on this
    site ("/search?category=sports") or an https:// URL. That rules out
    javascript:, data: and protocol-relative ("//evil.example") links."""
    if raw is None:
        return None
    url = raw.strip()
    if not url:
        return None
    if any(ch == "\\" or ord(ch) < 32 or ord(ch) == 127 for ch in url):
        # "/\\evil.example" is read by browsers as "//evil.example".
        raise HTTPException(status_code=422, detail="Link must not contain backslashes or control characters")
    if url.startswith("/") and not url.startswith("//"):
        return url
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc:
        return url
    raise HTTPException(
        status_code=422,
        detail="Link must be a page on this site (starting with /) or a full https:// address",
    )


def _validate_window(start_at: datetime | None, end_at: datetime | None) -> None:
    if start_at is not None and end_at is not None and start_at >= end_at:
        raise HTTPException(status_code=422, detail="The end time must be after the start time")


async def list_public(session: AsyncSession, placement: str | None = None) -> list[SiteBanner]:
    """What visitors see: enabled and inside its schedule window, decided
    here on the server — the browser is never trusted to hide a banner."""
    now = datetime.now(timezone.utc)
    query = (
        select(SiteBanner)
        .where(
            SiteBanner.enabled.is_(True),
            or_(SiteBanner.start_at.is_(None), SiteBanner.start_at <= now),
            or_(SiteBanner.end_at.is_(None), SiteBanner.end_at > now),
        )
        .order_by(SiteBanner.placement, SiteBanner.priority.asc(), SiteBanner.created_at.desc())
    )
    if placement is not None:
        if placement not in PLACEMENTS:
            raise HTTPException(status_code=422, detail="Unknown banner placement")
        query = query.where(SiteBanner.placement == placement).limit(MAX_LIVE_PER_PLACEMENT)
    return list((await session.execute(query)).scalars().all())


async def list_admin(session: AsyncSession) -> list[SiteBanner]:
    return list(
        (
            await session.execute(
                select(SiteBanner).order_by(
                    SiteBanner.placement, SiteBanner.priority.asc(), SiteBanner.created_at.desc()
                )
            )
        )
        .scalars()
        .all()
    )


async def create_banner(session: AsyncSession, *, admin_id: uuid.UUID, data: dict) -> SiteBanner:
    if data.get("placement", "home_hero") not in PLACEMENTS:
        raise HTTPException(status_code=422, detail="Unknown banner placement")
    _validate_window(data.get("start_at"), data.get("end_at"))
    async with session.begin():
        banner = SiteBanner(
            placement=data.get("placement", "home_hero"),
            title=data["title"].strip(),
            subtitle=(data.get("subtitle") or "").strip() or None,
            cta_label=(data.get("cta_label") or "").strip() or None,
            cta_url=clean_cta_url(data.get("cta_url")),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            created_by=admin_id,
        )
        session.add(banner)
        await session.flush()
        session.add(
            AuditLog(
                actor_id=admin_id,
                action="banner.created",
                entity_type="banner",
                entity_id=banner.id,
                extra_data={"title": banner.title, "placement": banner.placement},
            )
        )
    return banner


async def _load(session: AsyncSession, banner_id: uuid.UUID) -> SiteBanner:
    banner = (
        await session.execute(select(SiteBanner).where(SiteBanner.id == banner_id).with_for_update())
    ).scalar_one_or_none()
    if banner is None:
        raise HTTPException(status_code=404, detail="Banner not found")
    return banner


async def update_banner(
    session: AsyncSession, *, admin_id: uuid.UUID, banner_id: uuid.UUID, changes: dict
) -> SiteBanner:
    async with session.begin():
        banner = await _load(session, banner_id)
        if "placement" in changes and changes["placement"] is not None:
            if changes["placement"] not in PLACEMENTS:
                raise HTTPException(status_code=422, detail="Unknown banner placement")
            banner.placement = changes["placement"]
        if "title" in changes and changes["title"] is not None:
            banner.title = changes["title"].strip()
        # Nullable text fields: an explicit empty string clears them.
        for field in ("subtitle", "cta_label"):
            if field in changes:
                setattr(banner, field, (changes[field] or "").strip() or None)
        if "cta_url" in changes:
            banner.cta_url = clean_cta_url(changes["cta_url"])
        for field in ("enabled", "priority"):
            if field in changes and changes[field] is not None:
                setattr(banner, field, changes[field])
        for field in ("start_at", "end_at"):
            if field in changes:
                setattr(banner, field, changes[field])
        _validate_window(banner.start_at, banner.end_at)
        banner.updated_at = datetime.now(timezone.utc)
        session.add(
            AuditLog(
                actor_id=admin_id,
                action="banner.updated",
                entity_type="banner",
                entity_id=banner.id,
                extra_data={"fields": sorted(changes.keys())},
            )
        )
    return banner


async def set_banner_image(
    session: AsyncSession, *, admin_id: uuid.UUID, banner_id: uuid.UUID, content: bytes, storage
) -> SiteBanner:
    from app.modules.storage.base import UnsupportedFileError
    from app.modules.storage.images import BANNER_MAX_LONG_EDGE, optimize_image

    try:
        optimized, content_type, _size = optimize_image(content, max_long_edge=BANNER_MAX_LONG_EDGE)
    except UnsupportedFileError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    async with session.begin():
        banner = await _load(session, banner_id)
        try:
            url, key = await storage.save(optimized, content_type, key_prefix="banners")
        except UnsupportedFileError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        banner.image_url = url
        banner.image_storage_key = key
        banner.updated_at = datetime.now(timezone.utc)
        session.add(
            AuditLog(
                actor_id=admin_id,
                action="banner.image_replaced",
                entity_type="banner",
                entity_id=banner.id,
            )
        )
    return banner


async def delete_banner(session: AsyncSession, *, admin_id: uuid.UUID, banner_id: uuid.UUID) -> None:
    async with session.begin():
        banner = await _load(session, banner_id)
        session.add(
            AuditLog(
                actor_id=admin_id,
                action="banner.deleted",
                entity_type="banner",
                entity_id=banner.id,
                extra_data={"title": banner.title, "placement": banner.placement},
            )
        )
        await session.delete(banner)
