"""Normalization helpers for transaction counterparty evidence."""

from __future__ import annotations

import re
import unicodedata


_VPA_RE = re.compile(r"[a-z0-9._]+@[a-z]+", re.IGNORECASE)
_PREFIX_RE = re.compile(r"^(?:UPI[-/ ]|PAYTM\*|PHONEPE\*|GPAY\*|POS |ECOM |IMPS[-/ ])", re.IGNORECASE)


def extract_vpa(text: str) -> str | None:
    """Return the first UPI VPA in *text*, normalized to lowercase."""
    match = _VPA_RE.search(text or "")
    return match.group(0).lower() if match else None


def normalize_name(raw: str) -> str:
    """Produce the frozen, conservative matching key from a raw payee name."""
    value = unicodedata.normalize("NFKC", raw or "").upper().strip()
    value = _PREFIX_RE.sub("", value)
    value = re.sub(r"@\w+", "", value)
    value = re.sub(r"\b\d{4,}\b", "", value)
    value = re.sub(r"[^A-Z &]", " ", value)
    return " ".join(value.split())


def derive_name_key(description: str, vpa: str | None) -> str | None:
    """Remove VPA transport evidence from a description and normalize its name."""
    name = description or ""
    if vpa:
        name = re.sub(re.escape(vpa), "", name, flags=re.IGNORECASE)
    name = re.sub(r"^UPI-", "", name, flags=re.IGNORECASE)
    name = name.rstrip("- ")
    normalized = normalize_name(name)
    return normalized or None
