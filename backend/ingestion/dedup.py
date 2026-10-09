"""Deterministic transaction identity and duplicate keys."""

from __future__ import annotations

import hashlib

from .normalize import normalize_name


def make_dedup_key(
    upi_ref: str | None,
    date: str,
    amount_minor: int,
    direction: str,
    counterparty_raw: str,
) -> str:
    if upi_ref:
        return f"ref:{upi_ref}"
    evidence = "|".join(
        (date, str(amount_minor), direction, normalize_name(counterparty_raw))
    )
    return "fp:" + hashlib.sha256(evidence.encode("utf-8")).hexdigest()


def make_transaction_id(dedup_key: str) -> str:
    digest = hashlib.sha256(dedup_key.encode("utf-8")).hexdigest()
    return "t_" + digest[:12]
