"""
KeyService — envelope encryption + blind-index helpers.
Master key lives in MASTER_KEY_FILE (32 bytes). Auto-created in development if missing.
Uses AES-GCM. Separate MFA DEK derivation is prepared for later expansion.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class KeyService:
    def __init__(self) -> None:
        self._master_key: bytes | None = None

    def _ensure_master_key(self) -> bytes:
        if self._master_key is not None:
            return self._master_key

        settings = get_settings()
        path = Path(settings.master_key_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            key = path.read_bytes()
            if len(key) != 32:
                raise RuntimeError(f"Master key at {path} must be exactly 32 bytes")
            self._master_key = key
            return key

        if settings.app_env == "production":
            raise RuntimeError(
                f"Master key file missing in production: {path}. "
                "Generate offline and place securely."
            )

        # Dev: auto-generate
        key = secrets.token_bytes(32)
        path.write_bytes(key)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        logger.warning("master_key_auto_created", path=str(path))
        self._master_key = key
        return key

    @property
    def master_key(self) -> bytes:
        return self._ensure_master_key()

    def encrypt(self, plaintext: bytes | str, *, aad: bytes | None = None) -> bytes:
        """AES-GCM encrypt. Returns nonce (12) || ciphertext+tag."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")
        key = self.master_key
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext, aad)
        return nonce + ct

    def decrypt(self, blob: bytes, *, aad: bytes | None = None) -> bytes:
        if len(blob) < 13:
            raise ValueError("Invalid ciphertext")
        nonce, ct = blob[:12], blob[12:]
        aesgcm = AESGCM(self.master_key)
        return aesgcm.decrypt(nonce, ct, aad)

    def encrypt_str(self, plaintext: str, *, aad: bytes | None = None) -> str:
        """Return url-safe base64 of encrypted blob (for DB storage)."""
        import base64
        return base64.urlsafe_b64encode(self.encrypt(plaintext, aad=aad)).decode("ascii")

    def decrypt_str(self, blob_b64: str, *, aad: bytes | None = None) -> str:
        import base64
        raw = base64.urlsafe_b64decode(blob_b64.encode("ascii"))
        return self.decrypt(raw, aad=aad).decode("utf-8")

    def blind_index(self, value: str, *, context: str = "email") -> str:
        """
        HMAC-SHA256 blind index (hex). Useful for unique lookups without
        storing the raw value in a searchable column long-term.
        """
        key = self.master_key
        h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
        h.update(context.encode("utf-8"))
        h.update(b"|")
        h.update(value.strip().lower().encode("utf-8"))
        return h.finalize().hex()


# Singleton for the process
_key_service: KeyService | None = None


def get_key_service() -> KeyService:
    global _key_service
    if _key_service is None:
        _key_service = KeyService()
    return _key_service
