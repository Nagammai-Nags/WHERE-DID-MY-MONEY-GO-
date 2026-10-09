from __future__ import annotations

from datetime import date


CATEGORIES = [
    "Food",
    "Transport",
    "Groceries",
    "Entertainment",
    "Shopping",
    "Bills",
    "Education",
    "Uncategorized",
]


def detect_intent(question: str) -> str:
    normalized = question.casefold()

    if "budget" in normalized:
        return "budget_status"
    if "small" in normalized:
        return "small_txn_total"
    if any(word in normalized for word in ("merchant", "vendor", "shops")):
        return "top_merchants"

    for category in CATEGORIES:
        if category == "Uncategorized":
            continue
        if category.casefold() in normalized:
            return "category_total"

    if any(word in normalized for word in ("most", "top", "biggest", "largest")):
        return "top_categories"
    if "how much" in normalized or "total" in normalized:
        return "total_spend"
    return "unsupported"


def _previous_month(month: str) -> str:
    year, month_num = [int(part) for part in month.split("-")]
    if month_num == 1:
        return f"{year - 1}-12"
    return f"{year}-{month_num - 1:02d}"


def detect_period(question: str, reference_month: str) -> tuple[str, str]:
    if "last month" in question.casefold():
        month = _previous_month(reference_month)
    else:
        month = reference_month

    year, month_num = [int(part) for part in month.split("-")]
    start = date(year, month_num, 1)
    if month_num == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month_num + 1, 1)
    end = date.fromordinal(next_month.toordinal() - 1)
    return start.isoformat(), end.isoformat()
