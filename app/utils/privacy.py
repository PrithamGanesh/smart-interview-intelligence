"""PII masking utilities."""

from __future__ import annotations

import re


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")


def mask_email(email: str | None) -> str | None:
    """Mask an email address while keeping it useful for human review."""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
    return f"{masked_local}@{domain}"


def mask_pii(text: str) -> str:
    """Mask common PII before long-term storage or logging."""
    masked = EMAIL_PATTERN.sub(lambda match: mask_email(match.group(0)) or "", text or "")
    return PHONE_PATTERN.sub("[phone-redacted]", masked)
