"""Application-level field encryption (DPDP Rules 2025 r.6(1)(a)).

Identity numbers, PAN, GSTIN, bank account numbers, broker payout details
and admin TOTP secrets are stored as ``enc:v1:<nonce>.<ciphertext>`` using
AES-256-GCM with a key from ``FIELD_ENCRYPTION_KEY``. Values that do not
carry the prefix are treated as legacy plaintext, so a database can be
migrated row by row (alembic revision j2_encrypt_sensitive_fields).

Key rotation: put the new key in FIELD_ENCRYPTION_KEY and the previous one
in FIELD_ENCRYPTION_OLD_KEYS, then run ``python -m scripts.rotate_field_key``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

PREFIX = "enc:v1:"
_log = logging.getLogger("groundkart.crypto")
_warned = False


def _decode_key(raw: str) -> bytes:
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise ValueError("FIELD_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def _current_key() -> bytes:
    global _warned
    if settings.field_encryption_key:
        return _decode_key(settings.field_encryption_key)
    if settings.environment.lower() in ("prod", "production"):
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not set")
    if not _warned:
        _log.warning("FIELD_ENCRYPTION_KEY not set; using a development key derived from JWT_SECRET_KEY")
        _warned = True
    return hashlib.sha256(b"groundkart-dev-field-key:" + settings.jwt_secret_key.encode()).digest()


def _all_keys() -> list[bytes]:
    keys = [_current_key()]
    for raw in (settings.field_encryption_old_keys or "").split(","):
        if raw.strip():
            keys.append(_decode_key(raw.strip()))
    return keys


def is_encrypted(value: str | None) -> bool:
    return bool(value) and value.startswith(PREFIX)


def encrypt(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    if is_encrypted(value):
        return value
    nonce = os.urandom(12)
    ct = AESGCM(_current_key()).encrypt(nonce, value.encode("utf-8"), PREFIX.encode())
    return PREFIX + base64.urlsafe_b64encode(nonce).decode() + "." + base64.urlsafe_b64encode(ct).decode()


def decrypt(value: str | None) -> str | None:
    if not is_encrypted(value):
        return value  # legacy plaintext or empty
    body = value[len(PREFIX):]
    nonce_b64, ct_b64 = body.split(".", 1)
    nonce, ct = base64.urlsafe_b64decode(nonce_b64), base64.urlsafe_b64decode(ct_b64)
    last_error: Exception | None = None
    for key in _all_keys():
        try:
            return AESGCM(key).decrypt(nonce, ct, PREFIX.encode()).decode("utf-8")
        except Exception as exc:  # wrong key: try the next one
            last_error = exc
    raise ValueError("Could not decrypt field with any configured key") from last_error


def mask(value: str | None, visible: int = 4) -> str | None:
    """'ABCDE1234F' -> '••••••234F'. Works on encrypted or plain input."""
    plain = decrypt(value)
    if not plain:
        return plain
    keep = plain[-visible:] if len(plain) > visible else plain[-1:]
    return "•" * max(len(plain) - len(keep), 4) + keep


def keyed_hash(value: str, purpose: str) -> str:
    """Stable, non-reversible identifier for lookups and rate limits (IP
    addresses, phone numbers). HMAC so a dictionary of all phone numbers
    cannot be matched without the key."""
    key = hmac.new(_current_key(), purpose.encode(), hashlib.sha256).digest()
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()[:40]


# --- SQLAlchemy column type -------------------------------------------------
from sqlalchemy.types import Text as _Text, TypeDecorator as _TypeDecorator  # noqa: E402


class EncryptedText(_TypeDecorator):
    """Text column that is encrypted on write and decrypted on read, so no
    code path can forget to encrypt. Raw SQL (backups, the admin database
    viewer, psql) only ever sees ``enc:v1:...``."""

    impl = _Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value) if isinstance(value, str) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return decrypt(value)
        except Exception:
            _log.error("undecryptable field value (wrong FIELD_ENCRYPTION_KEY?)")
            return None
