"""TOTP MFA helpers (pyotp). Secrets are never stored in plaintext — encrypt via KeyService."""

import base64
import io

import pyotp
import qrcode

from app.core.config import get_settings


def generate_totp_secret() -> str:
    """Return a new base32 secret."""
    return pyotp.random_base32()


def get_totp(secret: str) -> pyotp.TOTP:
    settings = get_settings()
    return pyotp.TOTP(
        secret,
        digits=settings.mfa_totp_digits,
        interval=settings.mfa_totp_interval,
    )


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    totp = get_totp(secret)
    return bool(totp.verify(code, valid_window=valid_window))


def get_provisioning_uri(secret: str, email: str) -> str:
    settings = get_settings()
    totp = get_totp(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.mfa_issuer)


def generate_qr_base64(provisioning_uri: str) -> str:
    """Return a data-URI-friendly base64 PNG of the QR code."""
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
