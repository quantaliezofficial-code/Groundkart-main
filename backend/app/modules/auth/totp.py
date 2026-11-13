"""RFC 6238 time-based one-time passwords for admin two-step sign-in.

Implemented with the standard library (HMAC-SHA1, 30-second steps, 6
digits) so it works with any authenticator app (Google Authenticator,
Microsoft Authenticator, 1Password, Aegis). Secrets are stored encrypted
(app/modules/core/crypto.py); recovery codes are stored as Argon2 hashes.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP = 30
DIGITS = 6


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code(secret: str, counter: int) -> str:
    padded = secret + "=" * (-len(secret) % 8)
    key = base64.b32decode(padded, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def current_step(at: float | None = None) -> int:
    return int((at if at is not None else time.time()) // STEP)


def now(secret: str) -> str:
    return _code(secret, current_step())


def verify(secret: str, code: str, *, last_used_step: int | None = None, window: int = 1) -> int | None:
    """Returns the matched time step (to store and prevent replay) or None."""
    code = (code or "").strip().replace(" ", "")
    if not (code.isdigit() and len(code) == DIGITS):
        return None
    step = current_step()
    for candidate in range(step - window, step + window + 1):
        if last_used_step is not None and candidate <= last_used_step:
            continue
        if hmac.compare_digest(_code(secret, candidate), code):
            return candidate
    return None


def provisioning_uri(secret: str, account: str, issuer: str = "GroundKart") -> str:
    return f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={secret}&issuer={quote(issuer)}&digits={DIGITS}&period={STEP}"


def new_recovery_codes(n: int = 10) -> list[str]:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ["-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(2)) for _ in range(n)]
