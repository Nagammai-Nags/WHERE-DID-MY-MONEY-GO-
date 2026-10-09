"""Deterministic analytics over the shared transaction repository."""
from __future__ import annotations
import calendar
from datetime import date, datetime
from collections import defaultdict

from . import repo
from .models import SMALL_THRESHOLD_MINOR, signed_spend_minor

def reference_month() -> str:
    rows = repo.list_transactions(limit=1)
    if rows:
        return rows[0]["date"][:7]
    return date.today().strftime("%Y-%m")

def month_bounds(month: str) -> tuple[str, str]:
    parsed = datetime.strptime(month, "%Y-%m").date()
    last = calendar.monthrange(parsed.year, parsed.month)[1]
    return f"{parsed.year:04d}-{parsed.month:02d}-01", f"{parsed.year:04d}-{parsed.month:02d}-{last:02d}"

def net_spend(date_from: str, date_to: str, category: str | None = None) -> int:
    rows = repo.list_transactions(date_from, date_to, category=category)
    return sum(signed_spend_minor(row) for row in rows)

def income_total(date_from: str, date_to: str) -> int:
    return sum(r["amount_minor"] for r in repo.list_transactions(date_from, date_to, txn_type="INCOME"))

def _period(date_from: str | None, date_to: str | None) -> tuple[str, str]:
    if date_from is not None and date_to is not None:
        return date_from, date_to
    start, end = month_bounds(reference_month())
    return date_from or start, date_to or end

def summary(date_from: str | None = None, date_to: str | None = None,
            small_threshold_minor: int = SMALL_THRESHOLD_MINOR) -> dict:
    start, end = _period(date_from, date_to)
    rows = repo.list_transactions(start, end, limit=100000)
    spend_rows = [r for r in rows if r["txn_type"] in ("EXPENSE", "REFUND")]
    spend = sum(signed_spend_minor(r) for r in spend_rows)
    income = sum(r["amount_minor"] for r in rows if r["txn_type"] == "INCOME")
    categories: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    merchants: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in spend_rows:
        signed = signed_spend_minor(row)
        category, merchant = row["category"], row["display_merchant"]
        categories[category][0] += signed
        categories[category][1] += 1
        merchants[merchant][0] += signed
        merchants[merchant][1] += 1
    by_category = [{"category": k, "total_minor": v[0], "count": v[1], "pct_bp": (v[0] * 10000 // spend if spend > 0 else 0)}
                   for k, v in categories.items() if v[0] > 0]
    by_category.sort(key=lambda x: (-x["total_minor"], x["category"]))
    top_merchants = [{"display_merchant": k, "total_minor": v[0], "count": v[1]}
                     for k, v in merchants.items() if v[0] > 0]
    top_merchants.sort(key=lambda x: (-x["total_minor"], x["display_merchant"]))
    small = [r for r in rows if r["txn_type"] == "EXPENSE" and r["amount_minor"] <= small_threshold_minor]
    return {
        "period": {"from": start, "to": end},
        "net_spend_minor": spend,
        "income_minor": income,
        "transactions_counted": len(spend_rows),
        "by_category": by_category,
        "top_merchants": top_merchants[:5],
        "small_payments": {"threshold_minor": small_threshold_minor, "count": len(small), "total_minor": sum(r["amount_minor"] for r in small)},
        "uncategorized_minor": next((x["total_minor"] for x in by_category if x["category"] == "Uncategorized"), 0),
        "unknown_merchant_count": sum(1 for r in rows if r["txn_type"] == "EXPENSE" and r["merchant_source"] == "UNKNOWN"),
    }
