"""
TRD §4 made concrete: signup/login/refresh/logout, plus the rate limiting
TRD §4 requires on login/signup specifically ("blunt brute-force and
credential-stuffing attempts").

The refresh-rotation reuse detection in rotate_refresh_token() is the part
worth reading carefully — it's the actual security property TRD §4 asks
for ("a stolen refresh token can only be used once before detection"), not
just token issuance/expiry.

check_login_rate_limit() is Postgres-backed, not Redis-backed — Redis was
removed from this project entirely per explicit client direction (see the
phase summary doc for this slice). Worth knowing if this trips you up
against an older mental model of this function: it now takes the request's
own AsyncSession, not a separate redis_client.
"""
from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from sqlalchemy import select, text, update, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.security import create_access_token, hash_password, verify_password
from app.models.core import RefreshToken, User

REFRESH_TOKEN_TTL = timedelta(days=30)
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 10
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60


def _hash_token(raw: str) -> str:
    """Same pattern as Booking.manage_token_hash (Decision Point B-2) — an
    opaque bearer credential gets hashed at rest, never stored raw."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_client_ip(request: Request) -> str:
    """The client's IP, for rate limiting.

    The FIRST X-Forwarded-For entry is whatever the client chose to send, so
    trusting it let anyone dodge per-IP rate limits by setting the header.
    Instead: X-Real-IP, which our nginx overwrites with the real peer
    address (deploy/nginx.conf), then the LAST X-Forwarded-For entry, which
    is the one our own proxy appended, then the socket peer."""
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        last = forwarded.split(",")[-1].strip()
        if last:
            return last
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


_RATE_LIMIT_WORDS = {"ratelimit", "login", "signup", "forgot", "reset", "refresh", "ticket", "comment", "user", "ip", "refcode", "refapply", "contact", "erase", "otp"}


def _hashed_rate_limit_key(key: str) -> str:
    """'ratelimit:login:9876543210' -> 'ratelimit:login:h:<hmac>'. Keeps the
    structural prefix readable for debugging and replaces the identifier
    (phone, email, IP, user id) with a keyed hash, so the table never holds
    personal data in clear text (DATA_MAP row 23)."""
    from app.modules.core.crypto import keyed_hash

    parts = key.split(":")
    i = 0
    while i < len(parts) and parts[i] in _RATE_LIMIT_WORDS:
        i += 1
    ident = ":".join(parts[i:])
    if not ident or ident.startswith("h:"):
        return key
    return ":".join(parts[:i] + ["h", keyed_hash(ident, "ratelimit")])


async def check_rate_limit(
    session: AsyncSession,
    key: str,
    max_attempts: int = LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
    window_seconds: int = LOGIN_RATE_LIMIT_WINDOW_SECONDS,
) -> None:
    """Atomic, Postgres-backed sliding-window rate limit and timeout mechanism.
    Normalizes key whitespace/casing. Returns exact retry-after seconds in standard
    Retry-After response header and detail message when limit is exceeded.
    """
    normalized_key = _hashed_rate_limit_key(":".join(part.strip().lower() for part in key.split(":")))
    async with session.begin():
        result = await session.execute(
            text(
                """
                INSERT INTO login_rate_limits (key, window_start, attempt_count)
                VALUES (:key, now(), 1)
                ON CONFLICT (key) DO UPDATE SET
                    attempt_count = CASE
                        WHEN login_rate_limits.window_start < now() - make_interval(secs => :window_seconds)
                        THEN 1
                        ELSE login_rate_limits.attempt_count + 1
                    END,
                    window_start = CASE
                        WHEN login_rate_limits.window_start < now() - make_interval(secs => :window_seconds)
                        THEN now()
                        ELSE login_rate_limits.window_start
                    END
                RETURNING attempt_count,
                          GREATEST(1, CEIL(EXTRACT(EPOCH FROM (login_rate_limits.window_start + make_interval(secs => :window_seconds) - now())))::int) AS retry_after
                """
            ),
            {"key": normalized_key, "window_seconds": float(window_seconds)},
        )
        row = result.one()
        count = row[0]
        retry_after = row[1]

    if count > max_attempts:
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts — try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after), "code": "rate_limited"},
        )


async def check_login_rate_limit(session: AsyncSession, key: str) -> None:
    """Backwards-compatible wrapper for existing login and test call sites."""
    await check_rate_limit(
        session,
        key,
        max_attempts=LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds=LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )


async def cleanup_expired_rate_limits(session: AsyncSession, older_than_seconds: int = 3600) -> int:
    """Deletes rate limit entries older than older_than_seconds to keep
    the login_rate_limits table compact and performant."""
    async with session.begin():
        result = await session.execute(
            text(
                """
                DELETE FROM login_rate_limits
                WHERE window_start < now() - make_interval(secs => :older_than_seconds)
                """
            ),
            {"older_than_seconds": float(older_than_seconds)},
        )
        return result.rowcount


async def signup(session: AsyncSession, name: str, phone: str, password: str, email: str | None = None) -> User:
    try:
        async with session.begin():
            # Check if email is provided and exists, or if phone exists
            query_conditions = [User.phone == phone]
            if email is not None:
                query_conditions.append(User.email == email)
                
            existing = await session.execute(select(User).where(or_(*query_conditions)))
            if existing.scalar_one_or_none() is not None:
                raise HTTPException(status_code=409, detail="An account with this phone or email already exists")

            user = User(
                name=name,
                email=email,
                phone=phone,
                password_hash=hash_password(password),
                role="customer",  # owner accounts go through a separate verification flow — not this endpoint
            )
            session.add(user)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="An account with this phone or email already exists")

    return user


async def forgot_password(session: AsyncSession, login_id: str) -> None:
    from app.models.core import User, PasswordResetRequest

    async with session.begin():
        result = await session.execute(
            select(User).where((User.email == login_id) | (User.phone == login_id))
        )
        user = result.scalar_one_or_none()
        if not user or user.deleted_at is not None or user.suspended_at is not None:
            return

        existing = await session.execute(
            select(PasswordResetRequest).where(
                PasswordResetRequest.user_id == user.id,
                PasswordResetRequest.status == "pending",
            )
        )
        if existing.scalar_one_or_none() is not None:
            return

        req = PasswordResetRequest(
            user_id=user.id,
            source_type="user",
            status="pending",
            token_hash=None,
            expires_at=None,
            reason="User Forgot Password",
        )
        session.add(req)


async def reset_password(session: AsyncSession, token: str, new_password: str) -> None:
    from app.models.core import User, PasswordResetRequest, RefreshToken, AuditLog
    from app.modules.auth.security import hash_password
    from datetime import datetime, timezone

    token_hash = _hash_token(token)
    
    async with session.begin():
        result = await session.execute(
            select(PasswordResetRequest).where(PasswordResetRequest.token_hash == token_hash)
        )
        req = result.scalar_one_or_none()
        
        if req is None or req.used_at is not None or req.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
            
        user = await session.get(User, req.user_id)
        if not user or user.deleted_at is not None or user.suspended_at is not None:
            raise HTTPException(status_code=400, detail="Invalid account state")
            
        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        user.password_changed_at = datetime.now(timezone.utc)
        req.used_at = datetime.now(timezone.utc)
        
        # Invalidate all active sessions for this user on password reset
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        
        # Log it
        session.add(AuditLog(
            actor_id=user.id,
            action="user.password_reset",
            entity_type="user",
            entity_id=user.id,
            extra_data={"source_type": req.source_type}
        ))

def _build_refresh_token(user_id: uuid.UUID) -> tuple[RefreshToken, str]:
    raw = secrets.token_urlsafe(32)
    rt = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc) + REFRESH_TOKEN_TTL,
    )
    return rt, raw


async def login(session: AsyncSession, login_id: str, password: str, otp: str | None = None) -> tuple[User, str, str]:
    """Returns (user, access_token, raw_refresh_token).

    Admins who have enrolled in two-step sign-in must also send ``otp``: a
    current authenticator code or one unused recovery code. Without it the
    response is 401 ``two_factor_required`` (only after the password has
    been checked, so it reveals nothing to someone without the password)."""
    invalid = HTTPException(status_code=401, detail="Incorrect email, phone or password")
    amr = ["pwd"]

    async with session.begin():
        result = await session.execute(select(User).where((User.email == login_id) | (User.phone == login_id)))
        user = result.scalar_one_or_none()

        # Deliberately the same error for "no such user", "wrong
        # password", "deleted", and now "suspended" (Decision Point C-14)
        # — distinguishing any of these lets an attacker enumerate valid
        # emails, or learn which accounts are currently suspended.
        if user is None or user.deleted_at is not None or user.suspended_at is not None:
            raise invalid
        if not verify_password(password, user.password_hash):
            raise invalid

        if user.totp_enabled_at is not None:
            if not otp:
                raise HTTPException(status_code=401, detail="two_factor_required")
            if not _check_second_factor(user, otp):
                raise HTTPException(status_code=401, detail="Invalid two-step code")
            amr = ["pwd", "otp"]

        user.last_active_at = datetime.now(timezone.utc)
        user.inactivity_warned_at = None
        refresh_token_row, raw_refresh = _build_refresh_token(user.id)
        session.add(refresh_token_row)

    access_token = create_access_token(user.id, user.role, amr=amr)
    return user, access_token, raw_refresh


def _check_second_factor(user: User, code: str) -> bool:
    """TOTP code (replay-protected) or a single-use recovery code."""
    from app.modules.auth import totp
    from app.modules.core.crypto import decrypt

    secret = decrypt(user.totp_secret_enc)
    if secret:
        step = totp.verify(secret, code, last_used_step=user.totp_last_used_step)
        if step is not None:
            user.totp_last_used_step = step
            return True
    normalised = code.strip().upper()
    hashes = list(user.totp_recovery_hashes or [])
    for i, h in enumerate(hashes):
        if verify_password(normalised, h):
            hashes.pop(i)
            user.totp_recovery_hashes = hashes
            return True
    return False


async def rotate_refresh_token(session: AsyncSession, raw_token: str) -> tuple[str, User]:
    """Returns (new_raw_refresh_token, user). Raises 401 on anything wrong —
    invalid, expired, or reused — distinguishing reuse from the others only
    in the side effect (full session revocation), not in what the caller
    sees, same reasoning as login()'s merged error message.
    """
    token_hash = _hash_token(raw_token)
    reuse_detected = False

    async with session.begin():
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        rt = result.scalar_one_or_none()

        if rt is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if rt.revoked_at is not None:
            # Reuse of an already-rotated-away token. Either a client bug
            # replayed a stale token, or a stolen copy is being used after
            # the legitimate owner already moved past it — TRD §4 says
            # treat this as detected theft, not a retry. Revoke every
            # active session for this user; everything currently logged in
            # has to re-authenticate.
            #
            # Deliberately NOT raising inside this `async with` block: an
            # exception here would roll back the whole transaction,
            # including the revocation UPDATE below — undoing the exact
            # side effect this branch exists to cause. Flag it and raise
            # only after the block exits cleanly and commits.
            reuse_detected = True
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == rt.user_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=datetime.now(timezone.utc))
            )
        elif rt.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Refresh token expired")
        else:
            user = await session.get(User, rt.user_id)
            if user is not None:
                user.last_active_at = datetime.now(timezone.utc)
                user.inactivity_warned_at = None

            new_raw = secrets.token_urlsafe(32)
            new_rt = RefreshToken(
                user_id=rt.user_id,
                token_hash=_hash_token(new_raw),
                expires_at=datetime.now(timezone.utc) + REFRESH_TOKEN_TTL,
            )
            session.add(new_rt)
            await session.flush()

            rt.revoked_at = datetime.now(timezone.utc)
            rt.replaced_by_id = new_rt.id

    if reuse_detected:
        raise HTTPException(
            status_code=401,
            detail="Refresh token reuse detected — all sessions have been signed out",
            headers={"code": "refresh_reuse_detected"},
        )

    return new_raw, user


async def logout(session: AsyncSession, raw_token: str) -> None:
    """Revoke just this one session, not every session — a deliberate
    asymmetry with the reuse-detection path above, which revokes
    everything. A normal logout from one device shouldn't sign the user out
    of their other devices; a detected theft should."""
    token_hash = _hash_token(raw_token)
    async with session.begin():
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
