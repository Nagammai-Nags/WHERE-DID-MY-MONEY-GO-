"""Member 1 core HTTP endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Query
from . import analytics, repo
from .models import ApiError, CATEGORIES, parse_date

router = APIRouter()

def _validated_period(date_from: str | None, date_to: str | None) -> tuple[str | None, str | None]:
    try:
        start = parse_date(date_from) if date_from is not None else None
        end = parse_date(date_to) if date_to is not None else None
    except ValueError as exc:
        raise ApiError(422, "VALIDATION_ERROR", str(exc)) from exc
    if start and end and start > end:
        raise ApiError(422, "VALIDATION_ERROR", "from must be on or before to")
    return start, end

@router.get("/healthz")
def healthz() -> dict:
    import os
    value = {"status": "ok"}
    if os.environ.get("WDMMG_DB") == ":memory:":
        value["db"] = "memory"
    return value

@router.get("/categories")
def categories() -> dict:
    return {"items": CATEGORIES}

@router.get("/transactions")
def transactions(date_from: str | None = Query(default=None, alias="from"),
                 date_to: str | None = Query(default=None, alias="to"),
                 category: str | None = None, txn_type: str | None = Query(default=None, alias="type"),
                 merchant_source: str | None = None, limit: int = Query(default=500, ge=1, le=1000),
                 offset: int = Query(default=0, ge=0)) -> dict:
    start, end = _validated_period(date_from, date_to)
    items = repo.list_transactions(start, end, category, txn_type, merchant_source, limit, offset)
    return {"items": items, "count": len(items)}

@router.get("/analytics/summary")
def analytics_summary(date_from: str | None = Query(default=None, alias="from"),
                      date_to: str | None = Query(default=None, alias="to")) -> dict:
    start, end = _validated_period(date_from, date_to)
    return analytics.summary(start, end)

@router.post("/dev/reset")
def dev_reset() -> dict:
    repo.reset_all()
    return {"status": "ok"}
