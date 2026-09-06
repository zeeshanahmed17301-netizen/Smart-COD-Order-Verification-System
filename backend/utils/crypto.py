"""Application-level field encryption helpers.

Provides ``EncryptedCharField`` and ``EncryptedTextField`` which transparently
encrypt values at write time and decrypt at read time using Fernet (AES-128-CBC
with HMAC-SHA256 authentication).

Migration safety
----------------
Both fields tolerate legacy plaintext rows: if the stored value cannot be
decrypted as a Fernet token, it is returned as-is. The next write will
re-encrypt it. The ``encrypt_store_secrets`` management command can be run to
rewrite all rows in one pass.

Key management
--------------
The encryption key is read from ``settings.FIELD_ENCRYPTION_KEY`` (a
URL-safe base64-encoded 32-byte key). The base settings derive a deterministic
key from ``SECRET_KEY`` for development convenience; production settings
refuse to start without an explicit ``DJANGO_FIELD_ENCRYPTION_KEY``.
"""
from __future__ import annotations

from functools import lru_cache

from django.conf import settings
from django.db import models


@lru_cache(maxsize=1)
def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The 'cryptography' package is required for encrypted model fields."
        ) from exc

    key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
    if not key:
        raise RuntimeError(
            "FIELD_ENCRYPTION_KEY is not configured. Set DJANGO_FIELD_ENCRYPTION_KEY "
            "to a Fernet-compatible 32-byte URL-safe base64 key."
        )
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


def encrypt_str(value: str) -> str:
    """Encrypt a unicode string and return a Fernet token (str)."""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_str(token: str) -> str:
    """Decrypt a Fernet token. Raises ``cryptography.fernet.InvalidToken`` on failure."""
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def _try_decrypt(value: str) -> str:
    """Best-effort decrypt. Returns the original value if it isn't a Fernet token.

    This keeps reads working for legacy plaintext rows during the rollout window.
    """
    if not value:
        return value
    try:
        from cryptography.fernet import InvalidToken
    except ImportError:  # pragma: no cover
        return value
    try:
        return decrypt_str(value)
    except InvalidToken:
        return value
    except Exception:
        # Defensive: malformed bytes should never crash a read.
        return value


def _is_encrypted(value: str) -> bool:
    if not value:
        return False
    try:
        from cryptography.fernet import InvalidToken
    except ImportError:  # pragma: no cover
        return False
    try:
        decrypt_str(value)
        return True
    except (InvalidToken, Exception):
        return False


class _EncryptedFieldMixin:
    """Shared encrypt-on-write / decrypt-on-read behavior."""

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return _try_decrypt(value)

    def to_python(self, value):  # called by forms / full_clean
        if value is None:
            return value
        if isinstance(value, str) and _is_encrypted(value):
            return _try_decrypt(value)
        return value

    def get_prep_value(self, value):
        if value is None:
            return value
        value = str(value)
        if value == "":
            return value
        if _is_encrypted(value):
            # Idempotent: do not double-encrypt.
            return value
        return encrypt_str(value)


class EncryptedCharField(_EncryptedFieldMixin, models.CharField):
    """A CharField whose value is encrypted at rest with Fernet.

    Note: ``max_length`` must be large enough to hold the base64 token, which
    is roughly ``ceil(plaintext_len / 3) * 4 + 100`` bytes of overhead.
    Use 512 unless you know the plaintext is very small.
    """

    description = "CharField with transparent Fernet encryption at rest"


class EncryptedTextField(_EncryptedFieldMixin, models.TextField):
    """A TextField whose value is encrypted at rest with Fernet."""

    description = "TextField with transparent Fernet encryption at rest"
