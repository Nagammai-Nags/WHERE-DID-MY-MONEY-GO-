"""Custom date-range graph analytics for transaction exploration."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Query

from . import repo
from .models import ApiError, parse_date, signed_spend_minor

router = APIRouter()


def _validated_period(date_from: str, date_to: str) -> tuple[str, str]:
    try:
        start = parse_date(date_from)
        end = parse_date(date_to)
    except ValueError as exc:
        raise ApiError(422, "VALIDATION_ERROR", str(exc)) from exc
    if start > end:
        raise ApiError(422, "VALIDATION_ERROR", "from must be on or before to")
    return start, end


def _date_range(start: str, end: str) -> list[str]:
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    days = []
    while current <= last:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _previous_period(start: str, end: str) -> tuple[str, str]:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    span_days = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=span_days - 1)
    return previous_start.isoformat(), previous_end.isoformat()


def _group_key(day: str, total_days: int) -> str:
    parsed = date.fromisoformat(day)
    if total_days > 366:
        return parsed.strftime("%Y-%m")
    if total_days > 62:
        monday = parsed - timedelta(days=parsed.weekday())
        return monday.isoformat()
    return day


def _transaction_payload(row: dict) -> dict:
    return {
        "transaction_id": row["transaction_id"],
        "date": row["date"],
        "display_merchant": row["display_merchant"],
        "category": row["category"],
        "txn_type": row["txn_type"],
        "amount_minor": row["amount_minor"],
        "counterparty_raw": row["counterparty_raw"],
    }


def _empty_response(start: str, end: str) -> dict:
    return {
        "period": {"from": start, "to": end, "grouping": "day", "days": len(_date_range(start, end))},
        "summary": {
            "net_spend_minor": 0,
            "income_minor": 0,
            "spending_transaction_count": 0,
            "average_daily_net_spend_minor": 0,
            "highest_merchant": None,
            "previous_period": None,
        },
        "time_series": [],
        "category_breakdown": [],
        "merchant_breakdown": [],
        "income_vs_expenditure": {"income_minor": 0, "expense_minor": 0, "refund_minor": 0, "net_spend_minor": 0},
        "activity": [],
        "transactions": [],
    }


def build_graph_analytics(rows: list[dict], date_from: str, date_to: str, previous_rows: list[dict] | None = None) -> dict:
    days = _date_range(date_from, date_to)
    if not rows:
        return _empty_response(date_from, date_to)

    total_days = len(days)
    grouping = "month" if total_days > 366 else "week" if total_days > 62 else "day"
    spend_rows = [row for row in rows if row["txn_type"] in ("EXPENSE", "REFUND")]
    net_spend = sum(signed_spend_minor(row) for row in spend_rows)
    income = sum(row["amount_minor"] for row in rows if row["txn_type"] == "INCOME")
    expense_minor = sum(row["amount_minor"] for row in rows if row["txn_type"] == "EXPENSE")
    refund_minor = sum(row["amount_minor"] for row in rows if row["txn_type"] == "REFUND")

    series: dict[str, dict[str, Any]] = {}
    activity: dict[str, dict[str, Any]] = {}
    for day in days:
        key = _group_key(day, total_days)
        series.setdefault(key, {"date": key, "net_spend_minor": 0, "income_minor": 0, "refund_minor": 0})
        activity.setdefault(key, {"date": key, "spending_transaction_count": 0})

    categories: dict[str, dict[str, Any]] = defaultdict(lambda: {"category": "", "total_minor": 0, "count": 0, "transactions": []})
    merchants: dict[str, dict[str, Any]] = defaultdict(lambda: {"display_merchant": "", "total_minor": 0, "count": 0, "transactions": []})

    for row in rows:
        key = _group_key(row["date"], total_days)
        signed = signed_spend_minor(row)
        if row["txn_type"] == "INCOME":
            series.setdefault(key, {"date": key, "net_spend_minor": 0, "income_minor": 0, "refund_minor": 0})
            series[key]["income_minor"] += row["amount_minor"]
            continue
        if row["txn_type"] not in ("EXPENSE", "REFUND"):
            continue

        series.setdefault(key, {"date": key, "net_spend_minor": 0, "income_minor": 0, "refund_minor": 0})
        activity.setdefault(key, {"date": key, "spending_transaction_count": 0})
        series[key]["net_spend_minor"] += signed
        if row["txn_type"] == "REFUND":
            series[key]["refund_minor"] += row["amount_minor"]
        activity[key]["spending_transaction_count"] += 1

        txn = _transaction_payload(row)
        category = row["category"]
        merchant = row["display_merchant"]
        categories[category]["category"] = category
        categories[category]["total_minor"] += signed
        categories[category]["count"] += 1
        categories[category]["transactions"].append(txn)
        merchants[merchant]["display_merchant"] = merchant
        merchants[merchant]["total_minor"] += signed
        merchants[merchant]["count"] += 1
        merchants[merchant]["transactions"].append(txn)

    category_items = [item for item in categories.values() if item["total_minor"] > 0]
    category_items.sort(key=lambda item: (-item["total_minor"], item["category"]))
    merchant_items = [item for item in merchants.values() if item["total_minor"] > 0]
    merchant_items.sort(key=lambda item: (-item["total_minor"], item["display_merchant"]))

    for item in merchant_items:
        item["average_minor"] = item["total_minor"] // item["count"] if item["count"] else 0
        item["share_bp"] = item["total_minor"] * 10000 // net_spend if net_spend > 0 else 0

    previous = None
    if previous_rows is not None:
        previous_start, previous_end = _previous_period(date_from, date_to)
        previous_net = sum(signed_spend_minor(row) for row in previous_rows if row["txn_type"] in ("EXPENSE", "REFUND"))
        delta = net_spend - previous_net
        previous = {
            "from": previous_start,
            "to": previous_end,
            "net_spend_minor": previous_net,
            "delta_minor": delta,
            "delta_pct_bp": (delta * 10000 // previous_net if previous_net > 0 else None),
        }

    return {
        "period": {"from": date_from, "to": date_to, "grouping": grouping, "days": total_days},
        "summary": {
            "net_spend_minor": net_spend,
            "income_minor": income,
            "spending_transaction_count": len(spend_rows),
            "average_daily_net_spend_minor": net_spend // total_days if total_days else 0,
            "highest_merchant": merchant_items[0] if merchant_items else None,
            "previous_period": previous,
        },
        "time_series": [series[key] for key in sorted(series)],
        "category_breakdown": category_items,
        "merchant_breakdown": merchant_items,
        "income_vs_expenditure": {
            "income_minor": income,
            "expense_minor": expense_minor,
            "refund_minor": refund_minor,
            "net_spend_minor": net_spend,
        },
        "activity": [activity[key] for key in sorted(activity)],
        "transactions": [_transaction_payload(row) for row in rows],
    }


@router.get("/analytics/graph")
def graph_analytics(date_from: str = Query(alias="from"), date_to: str = Query(alias="to")) -> dict:
    start, end = _validated_period(date_from, date_to)
    previous_start, previous_end = _previous_period(start, end)
    rows = repo.list_transactions(start, end, limit=100000)
    previous_rows = repo.list_transactions(previous_start, previous_end, limit=100000)
    return build_graph_analytics(rows, start, end, previous_rows)
