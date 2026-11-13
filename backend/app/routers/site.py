"""Super admin control of the public website: homepage content (with
versions), the image asset library, and review moderation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.core import AuditLog, Review, SiteAsset, User, Venue
from app.modules.auth.dependencies import get_admin_actor, get_super_admin_actor
from app.modules.site import content as site_content
from app.modules.storage.base import MAX_UPLOAD_SIZE_BYTES, UnsupportedFileError
from app.storage_client import get_file_storage

router = APIRouter()


# ── Homepage content ─────────────────────────────────────────────────────

@router.get("/api/v1/site/homepage", tags=["Site"])
async def public_homepage_content(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    response.headers["Cache-Control"] = "public, max-age=60"
    return site_content.view(await site_content.get(db))


class PublishBody(BaseModel):
    data: dict
    base_version: int | None = None
    note: str | None = Field(default=None, max_length=300)


@router.get("/api/v1/admin/site/homepage", tags=["Site"])
async def admin_homepage_content(actor: User = Depends(get_admin_actor), db: AsyncSession = Depends(get_db)) -> dict:
    view = site_content.view(await site_content.get(db))
    view["can_edit"] = bool(actor.is_super_admin)
    return view


@router.put("/api/v1/admin/site/homepage", tags=["Site"])
async def publish_homepage_content(body: PublishBody, actor: User = Depends(get_super_admin_actor), db: AsyncSession = Depends(get_db)) -> dict:
    row = await site_content.publish(db, actor_id=actor.id, data=body.data, base_version=body.base_version, note=body.note)
    return site_content.view(row)


@router.delete("/api/v1/admin/site/homepage", tags=["Site"])
async def reset_homepage_content(base_version: int | None = None, actor: User = Depends(get_super_admin_actor), db: AsyncSession = Depends(get_db)) -> dict:
    row = await site_content.publish(
        db, actor_id=actor.id, data={}, base_version=base_version, note="Reset to the built-in defaults", action="site_content.reset"
    )
    return site_content.view(row)


@router.get("/api/v1/admin/site/homepage/revisions", tags=["Site"])
async def homepage_revisions(actor: User = Depends(get_super_admin_actor), db: AsyncSession = Depends(get_db)) -> list[dict]:
    revs = await site_content.revisions(db)
    names = {}
    ids = {r.created_by for r in revs if r.created_by}
    if ids:
        names = dict((await db.execute(select(User.id, User.name).where(User.id.in_(ids)))).all())
    return [
        {
            "id": str(r.id),
            "version": r.version,
            "note": r.note,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "created_by": names.get(r.created_by),
            "sections": sorted((r.data or {}).keys()),
        }
        for r in revs
    ]


@router.post("/api/v1/admin/site/homepage/revisions/{revision_id}/restore", tags=["Site"])
async def restore_homepage_revision(revision_id: uuid.UUID, actor: User = Depends(get_super_admin_actor), db: AsyncSession = Depends(get_db)) -> dict:
    return site_content.view(await site_content.restore(db, actor_id=actor.id, revision_id=revision_id))


# ── Asset library ────────────────────────────────────────────────────────

def _asset_view(a: SiteAsset) -> dict:
    return {
        "id": str(a.id),
        "url": a.url,
        "label": a.label,
        "alt_text": a.alt_text,
        "width": a.width,
        "height": a.height,
        "size_bytes": a.size_bytes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/api/v1/admin/site/assets", tags=["Site"])
async def list_assets(actor: User = Depends(get_admin_actor), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (await db.execute(select(SiteAsset).order_by(SiteAsset.created_at.desc()))).scalars().all()
    return [_asset_view(a) for a in rows]


@router.post("/api/v1/admin/site/assets", status_code=201, tags=["Site"])
async def upload_asset(
    image: UploadFile = File(...),
    label: str = Form(..., min_length=1, max_length=80),
    alt_text: str = Form("", max_length=200),
    actor: User = Depends(get_super_admin_actor),
    db: AsyncSession = Depends(get_db),
    storage=Depends(get_file_storage),
) -> dict:
    from app.modules.storage.images import BANNER_MAX_LONG_EDGE, optimize_image

    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=422, detail="Upload a JPG, PNG or WebP image")
    data = await image.read()
    if len(data) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="Image exceeds the 10MB limit")
    try:
        optimized, content_type, (width, height) = optimize_image(data, max_long_edge=BANNER_MAX_LONG_EDGE)
        url, key = await storage.save(optimized, content_type, key_prefix="site")
    except UnsupportedFileError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    async with db.begin():
        asset = SiteAsset(
            url=url, storage_key=key, label=label.strip(), alt_text=alt_text.strip(),
            width=width, height=height, size_bytes=len(optimized), created_by=actor.id,
        )
        db.add(asset)
        await db.flush()
        db.add(AuditLog(actor_id=actor.id, action="site_asset.uploaded", entity_type="site_asset", entity_id=asset.id, extra_data={"label": asset.label}))
    return _asset_view(asset)


class AssetUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    alt_text: str | None = Field(default=None, max_length=200)


@router.patch("/api/v1/admin/site/assets/{asset_id}", tags=["Site"])
async def update_asset(asset_id: uuid.UUID, body: AssetUpdate, actor: User = Depends(get_super_admin_actor), db: AsyncSession = Depends(get_db)) -> dict:
    async with db.begin():
        asset = await db.get(SiteAsset, asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="Image not found")
        if body.label is not None:
            asset.label = body.label.strip()
        if body.alt_text is not None:
            asset.alt_text = body.alt_text.strip()
    return _asset_view(asset)


@router.delete("/api/v1/admin/site/assets/{asset_id}", status_code=204, tags=["Site"])
async def delete_asset(
    asset_id: uuid.UUID,
    actor: User = Depends(get_super_admin_actor),
    db: AsyncSession = Depends(get_db),
    storage=Depends(get_file_storage),
) -> Response:
    asset = await db.get(SiteAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Image not found")
    used = await site_content.asset_usage(db, asset.url)
    if used:
        raise HTTPException(status_code=409, detail="This image is in use: " + "; ".join(used) + ". Replace it there first.")
    key, label = asset.storage_key, asset.label
    await db.rollback()
    async with db.begin():
        row = await db.get(SiteAsset, asset_id)
        await db.delete(row)
        db.add(AuditLog(actor_id=actor.id, action="site_asset.deleted", entity_type="site_asset", entity_id=asset_id, extra_data={"label": label}))
    try:
        await storage.delete(key)
    except Exception:  # the row is gone; a stray file is harmless and logged by storage
        pass
    return Response(status_code=204)


# ── Review moderation ────────────────────────────────────────────────────

class ModerationBody(BaseModel):
    hidden: bool | None = None
    reason: str | None = Field(default=None, max_length=500)
    featured: bool | None = None


async def _recompute_rating(db: AsyncSession, venue_id: uuid.UUID) -> None:
    avg = (
        await db.execute(
            select(func.avg(Review.rating)).where(Review.venue_id == venue_id, Review.verified.is_(True), Review.hidden_at.is_(None))
        )
    ).scalar() or Decimal("0")
    venue = await db.get(Venue, venue_id)
    if venue is not None:
        venue.avg_rating = round(Decimal(str(avg)), 2)


@router.patch("/api/v1/admin/reviews/{review_id}/moderation", tags=["Site"])
async def moderate_review(review_id: uuid.UUID, body: ModerationBody, actor: User = Depends(get_super_admin_actor), db: AsyncSession = Depends(get_db)) -> dict:
    """Hide (with a reason) or feature a review. The customer's words and
    rating are never edited, and only verified-booking reviews can be
    featured, so moderation cannot turn into fake or selective praise."""
    async with db.begin():
        review = await db.get(Review, review_id, with_for_update=True)
        if review is None:
            raise HTTPException(status_code=404, detail="Review not found")
        changes: dict = {}
        if body.hidden is True and review.hidden_at is None:
            reason = (body.reason or "").strip()
            if len(reason) < 3:
                raise HTTPException(status_code=422, detail="Give a reason for hiding this review (it is kept in the audit log)")
            review.hidden_at = datetime.now(timezone.utc)
            review.hidden_reason = reason
            review.hidden_by = actor.id
            review.featured = False
            changes["hidden"] = reason
        elif body.hidden is False and review.hidden_at is not None:
            review.hidden_at = None
            review.hidden_reason = None
            review.hidden_by = None
            changes["hidden"] = False
        if body.featured is not None and body.featured != review.featured:
            if body.featured and (not review.verified or review.hidden_at is not None):
                raise HTTPException(status_code=422, detail="Only visible reviews from a completed booking can be featured")
            review.featured = body.featured
            changes["featured"] = body.featured
        if "hidden" in changes:
            await db.flush()
            await _recompute_rating(db, review.venue_id)
        if changes:
            db.add(AuditLog(actor_id=actor.id, action="review.moderated", entity_type="review", entity_id=review.id, extra_data=changes))
    return {
        "id": str(review.id),
        "hidden_at": review.hidden_at.isoformat() if review.hidden_at else None,
        "hidden_reason": review.hidden_reason,
        "featured": review.featured,
    }
