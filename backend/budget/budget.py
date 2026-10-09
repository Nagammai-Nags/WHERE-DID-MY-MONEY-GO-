from __future__ import annotations

import re
from typing import Any


MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _load_core_modules() -> tuple[Any, Any]:
    from backend import analytics, repo

    return analytics, repo


def validate_month(month: str) -> str:
    if not isinstance(month, str) or not MONTH_RE.match(month):
        raise ValueError("month must be YYYY-MM")
    return month


def compute_status(limit_minor: int | None, spent_minor: int) -> dict:
    if limit_minor is None:
        return {
            "limit_minor": None,
            "spent_minor": spent_minor,
            "remaining_minor": None,
            "pct_bp": None,
            "status": "NO_BUDGET",
        }

    remaining_minor = limit_minor - spent_minor
    pct_bp = spent_minor * 10000 // limit_minor
    if spent_minor > limit_minor:
        status = "EXCEEDED"
    elif pct_bp >= 8000:
        status = "WARNING"
    else:
        status = "OK"

    return {
        "limit_minor": limit_minor,
        "spent_minor": spent_minor,
        "remaining_minor": remaining_minor,
        "pct_bp": pct_bp,
        "status": status,
    }


def budget_status(month: str | None = None) -> dict:
    analytics, repo = _load_core_modules()

    if month is None:
        month = analytics.reference_month()
    else:
        validate_month(month)

    date_from, date_to = analytics.month_bounds(month)
    spent_minor = analytics.net_spend(date_from, date_to)
    limit_minor = repo.get_budget(month)

    return {"month": month, **compute_status(limit_minor, spent_minor)}
