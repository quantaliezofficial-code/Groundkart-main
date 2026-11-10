"""
Open Graph share pages.

The frontend is a single-page app: every URL returns the same index.html
and the real title, description and image are filled in by JavaScript.
WhatsApp, Facebook, LinkedIn, X, Slack and Telegram do not run JavaScript
when they build a link preview, so without this every shared venue link
shows the same generic GroundKart card.

These routes return a tiny, fully-formed HTML document for a venue or a
category with the right og:/twitter: tags. The web server sends link-
preview crawlers here (see deploy/nginx.conf) and sends people to the
normal app. A person who does land here is forwarded by a meta refresh.

Everything interpolated into the HTML is escaped. Venue names and
descriptions are owner-written text.
"""
from __future__ import annotations

from html import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.core import Venue

SITE_NAME = "GroundKart"
DEFAULT_DESCRIPTION = (
    "Find and book sports grounds, banquet halls, party venues, farmhouses and meeting "
    "spaces. Compare photos, prices and availability, then request your date."
)

UNIT_LABEL = {"hour": "per hour", "half_day": "per half day", "full_day": "per day"}

CATEGORY_COPY: dict[str, tuple[str, str]] = {
    "sports": (
        "Sports grounds, turfs and courts",
        "Book cricket grounds, football turfs and badminton courts by the hour.",
    ),
    "banquet_hall": (
        "Banquet halls and wedding venues",
        "Compare banquet halls and lawns for weddings, receptions and family functions.",
    ),
    "farmhouse": (
        "Farmhouses, resorts and outdoor venues",
        "Private farmhouses, resorts and lawns for celebrations and getaways.",
    ),
    "corporate": (
        "Meeting rooms and corporate event spaces",
        "Conference rooms and offsite venues for meetings, trainings and office parties.",
    ),
    "community_hall": (
        "Community halls",
        "Affordable halls for gatherings, ceremonies and local events.",
    ),
    "creative": (
        "Studios and creative spaces",
        "Photo studios, dance studios and creative spaces by the hour.",
    ),
}


def _public_base() -> str:
    return settings.public_app_url.rstrip("/")


def _truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:-") + "…"


def render_share_page(
    *,
    title: str,
    description: str,
    url: str,
    image: str,
    image_alt: str,
    og_type: str = "website",
    extra_meta: str = "",
) -> str:
    t, d, u, i, a = (escape(x, quote=True) for x in (title, description, url, image, image_alt))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{u}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:type" content="{escape(og_type, quote=True)}">
<meta property="og:locale" content="en_IN">
<meta property="og:url" content="{u}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:image" content="{i}">
<meta property="og:image:alt" content="{a}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{i}">
<meta name="twitter:image:alt" content="{a}">
{extra_meta}<meta http-equiv="refresh" content="0; url={u}">
</head>
<body>
<h1>{t}</h1>
<p>{d}</p>
<p><a href="{u}">Open on {SITE_NAME}</a></p>
</body>
</html>
"""


def default_page(path: str = "/") -> str:
    base = _public_base()
    return render_share_page(
        title=f"{SITE_NAME} — Book grounds, halls and event venues",
        description=DEFAULT_DESCRIPTION,
        url=f"{base}{path if path.startswith('/') else '/'}",
        image=f"{base}/og-image.jpg",
        image_alt=f"{SITE_NAME}: venues for weddings, parties, sports and corporate events",
    )


async def venue_page(session: AsyncSession, slug: str) -> str | None:
    """None when there is no publicly visible venue for this slug — the
    route answers that with the default card and a 404 status. A draft,
    pending, suspended or archived listing never gets a preview, so an
    unpublished venue can't leak through a shared link."""
    venue = (
        await session.execute(
            select(Venue)
            .options(selectinload(Venue.media))
            .where(Venue.slug == slug, Venue.status == "active", Venue.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if venue is None:
        return None

    base = _public_base()
    name = venue.display_name or venue.name
    images = [m for m in venue.media if getattr(m, "media_type", "image") == "image" and m.url]
    cover = next((m for m in images if m.is_cover), images[0] if images else None)
    image = cover.url if cover else f"{base}/og-image.jpg"

    price = f"From ₹{int(venue.base_price):,} {UNIT_LABEL.get(venue.unit_type, '')}".strip()
    facts = [price]
    if venue.capacity:
        facts.append(f"up to {venue.capacity} guests")
    lead = f"{', '.join(facts)}. "
    body = venue.tagline or venue.description or f"{venue.category.replace('_', ' ').title()} in {venue.city}."
    description = _truncate(lead + body, 200)

    extra = (
        f'<meta property="og:price:amount" content="{escape(str(venue.base_price), quote=True)}">\n'
        f'<meta property="og:price:currency" content="INR">\n'
    )
    return render_share_page(
        title=_truncate(f"{name}, {venue.city} | {SITE_NAME}", 70),
        description=description,
        url=f"{base}/venues/{venue.slug}",
        image=image,
        image_alt=f"{name} in {venue.city}",
        og_type="place",
        extra_meta=extra,
    )


def category_page(slug: str) -> str:
    """slug has already been validated by the route as [a-z0-9_-]+."""
    base = _public_base()
    normalized = slug.replace("-", "_")
    copy = (
        CATEGORY_COPY.get(normalized)
        or CATEGORY_COPY.get(normalized.removesuffix("s"))
        or ("Venues", DEFAULT_DESCRIPTION)
    )
    heading, description = copy
    return render_share_page(
        title=f"{heading} | {SITE_NAME}",
        description=description,
        url=f"{base}/categories/{slug}",
        image=f"{base}/og-image.jpg",
        image_alt=f"{heading} on {SITE_NAME}",
    )
