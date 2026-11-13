"""Homepage content the super admin edits.

The stored document holds only overrides: anything left out falls back to
the defaults in frontend/src/lib/homepageContent.ts, so "reset" is simply
an empty document. Text is shown as plain text (never HTML). Images must be
bundled site images (/img/...) or files from the asset library.

Numbers that are promises to customers (hold time, refund tiers, platform
fee) are not editable here: the site reads them from the booking rules, so
the homepage cannot claim something checkout does not do.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog, SiteAsset, SiteBanner, SiteContent, SiteContentRevision

HOMEPAGE = "homepage"
MAX_REVISIONS_LISTED = 30

# Values the search page's category filter understands.
OCCASION_CATEGORIES = frozenset(
    {
        "sports", "cricket", "football", "badminton", "tennis", "swimming",
        "banquet", "wedding_lawn", "reception", "party_hall", "birthday", "lounge",
        "corporate", "meeting_room", "conference", "coworking",
        "farmhouse", "resort", "photography", "dance_studio",
    }
)

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean(v: Any) -> Any:
    if isinstance(v, str):
        v = _CONTROL.sub("", v).strip()
        return v or None
    return v


class _Block(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _strip(cls, v):
        return _clean(v)


def _text(n: int):
    return Field(default=None, max_length=n)


class Hero(_Block):
    eyebrow: str | None = _text(120)
    title: str | None = _text(120)
    title_highlight: str | None = _text(80)
    subtitle: str | None = _text(400)
    image_url: str | None = _text(500)
    image_alt: str | None = _text(200)
    show_occasion_chips: bool | None = None


class Occasion(_Block):
    key: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9-]+$")
    label: str = Field(min_length=1, max_length=40)
    category: str
    image_url: str = Field(min_length=1, max_length=500)
    alt: str = Field(min_length=1, max_length=200)

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        if v not in OCCASION_CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(sorted(OCCASION_CATEGORIES))}")
        return v


class Sections(_Block):
    occasions: bool | None = None
    protections: bool | None = None
    preview: bool | None = None
    reviews: bool | None = None
    owners: bool | None = None
    partners: bool | None = None
    founder: bool | None = None
    faq: bool | None = None
    closing: bool | None = None


class TextBlock(_Block):
    title: str | None = _text(120)
    intro: str | None = _text(400)


class Owners(_Block):
    title: str | None = _text(120)
    bullets: list[str] | None = Field(default=None, max_length=5)
    image_url: str | None = _text(500)
    image_alt: str | None = _text(200)
    cta_label: str | None = _text(40)

    @field_validator("bullets")
    @classmethod
    def _bullets(cls, v):
        if v is None:
            return v
        out = [_clean(b) for b in v]
        if any(not b or len(b) > 200 for b in out):
            raise ValueError("each point must be 1 to 200 characters")
        return out


class TimelineItem(_Block):
    years: str = Field(min_length=1, max_length=30)
    org: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=300)


class Founder(_Block):
    eyebrow: str | None = _text(80)
    title: str | None = _text(120)
    body: str | None = _text(1200)
    name: str | None = _text(80)
    role: str | None = _text(120)
    link_url: str | None = _text(300)
    link_label: str | None = _text(60)
    timeline: list[TimelineItem] | None = Field(default=None, max_length=6)

    @field_validator("link_url")
    @classmethod
    def _link(cls, v):
        if v is None:
            return v
        if v.startswith("https://") or (v.startswith("/") and not v.startswith("//") and "\\" not in v):
            return v
        raise ValueError("link must start with https:// or be a page on this site (/...)")


class FaqItem(_Block):
    q: str = Field(min_length=3, max_length=200)
    a: str = Field(min_length=3, max_length=1200)


class Closing(_Block):
    title: str | None = _text(160)
    cta_label: str | None = _text(40)


class HomepageContent(_Block):
    hero: Hero | None = None
    occasions: list[Occasion] | None = Field(default=None, min_length=3, max_length=8)
    sections: Sections | None = None
    protections: TextBlock | None = None
    preview: TextBlock | None = None
    reviews: TextBlock | None = None
    owners: Owners | None = None
    founder: Founder | None = None
    faq: list[FaqItem] | None = Field(default=None, max_length=12)
    closing: Closing | None = None

    @field_validator("occasions")
    @classmethod
    def _unique_keys(cls, v):
        if v is not None and len({o.key for o in v}) != len(v):
            raise ValueError("each occasion needs a different key")
        return v


def _image_urls(doc: dict) -> list[str]:
    urls: list[str] = []
    for path in (("hero", "image_url"), ("owners", "image_url")):
        block = doc.get(path[0]) or {}
        if block.get(path[1]):
            urls.append(block[path[1]])
    for occ in doc.get("occasions") or []:
        urls.append(occ["image_url"])
    return urls


async def _check_images(session: AsyncSession, doc: dict) -> None:
    urls = _image_urls(doc)
    if not urls:
        return
    known = set((await session.execute(select(SiteAsset.url).where(SiteAsset.url.in_(urls)))).scalars())
    bad = [
        u
        for u in urls
        if u not in known and not (u.startswith("/img/") and ".." not in u and "\\" not in u and "//" not in u[1:])
    ]
    if bad:
        raise HTTPException(
            status_code=422,
            detail="Images must come from the asset library or the built-in site images: " + ", ".join(bad[:3]),
        )


def validate(data: Any) -> dict:
    try:
        model = HomepageContent.model_validate(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        raise HTTPException(status_code=422, detail=f"{where}: {first['msg']}") from exc
    return model.model_dump(exclude_none=True)


async def get(session: AsyncSession, key: str = HOMEPAGE) -> SiteContent | None:
    return await session.get(SiteContent, key)


def view(row: SiteContent | None) -> dict:
    if row is None:
        return {"data": {}, "version": 0, "updated_at": None}
    return {"data": row.data or {}, "version": row.version, "updated_at": row.updated_at.isoformat() if row.updated_at else None}


async def publish(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID,
    data: dict,
    base_version: int | None,
    note: str | None,
    action: str = "site_content.published",
) -> SiteContent:
    clean = validate(data)
    if session.in_transaction():  # the auth dependency has already read the actor
        await session.rollback()
    async with session.begin():
        await _check_images(session, clean)
        row = await session.get(SiteContent, HOMEPAGE, with_for_update=True)
        current = row.version if row else 0
        if base_version is not None and base_version != current:
            raise HTTPException(
                status_code=409,
                detail="Someone else published a change since you opened this page. Reload to see it, then make your edit again.",
            )
        if row is None:
            row = SiteContent(key=HOMEPAGE, data={}, version=0)
            session.add(row)
        row.data = clean
        row.version = current + 1
        row.updated_at = datetime.now(timezone.utc)
        row.updated_by = actor_id
        session.add(SiteContentRevision(key=HOMEPAGE, version=row.version, data=clean, note=(note or None), created_by=actor_id))
        session.add(
            AuditLog(
                actor_id=actor_id,
                action=action,
                entity_type="site_content",
                extra_data={"key": HOMEPAGE, "version": row.version, "sections": sorted(clean), "note": note},
            )
        )
    return row


async def revisions(session: AsyncSession) -> list[SiteContentRevision]:
    return list(
        (
            await session.execute(
                select(SiteContentRevision)
                .where(SiteContentRevision.key == HOMEPAGE)
                .order_by(SiteContentRevision.version.desc())
                .limit(MAX_REVISIONS_LISTED)
            )
        ).scalars()
    )


async def restore(session: AsyncSession, *, actor_id: uuid.UUID, revision_id: uuid.UUID) -> SiteContent:
    rev = await session.get(SiteContentRevision, revision_id)
    if rev is None or rev.key != HOMEPAGE:
        raise HTTPException(status_code=404, detail="Version not found")
    data, version = dict(rev.data or {}), rev.version
    return await publish(
        session,
        actor_id=actor_id,
        data=data,
        base_version=None,
        note=f"Restored version {version}",
        action="site_content.restored",
    )


async def asset_usage(session: AsyncSession, url: str) -> list[str]:
    """Where an asset is used, so it is never deleted from under the page."""
    used: list[str] = []
    row = await session.get(SiteContent, HOMEPAGE)
    doc = (row.data if row else None) or {}
    if (doc.get("hero") or {}).get("image_url") == url:
        used.append("Homepage hero")
    if (doc.get("owners") or {}).get("image_url") == url:
        used.append("Homepage owners section")
    for occ in doc.get("occasions") or []:
        if occ.get("image_url") == url:
            used.append(f"Occasion card \"{occ.get('label')}\"")
    banners = (await session.execute(select(SiteBanner.title).where(SiteBanner.image_url == url))).scalars().all()
    used += [f"Banner \"{t}\"" for t in banners]
    return used
