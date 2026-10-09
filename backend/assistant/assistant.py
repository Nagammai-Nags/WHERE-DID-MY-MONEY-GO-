from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from backend.assistant.intents import CATEGORIES, detect_intent, detect_period
from backend.budget.budget import budget_status


RUPEE_RE = re.compile(r"₹[0-9,]+\.\d{2}")


def _load_analytics() -> Any:
    from backend import analytics

    return analytics


def format_inr(minor: int) -> str:
    value = Decimal(minor) / Decimal(100)
    sign = "-" if value < 0 else ""
    value = abs(value)
    whole, fractional = f"{value:.2f}".split(".")
    if len(whole) > 3:
        last_three = whole[-3:]
        leading = whole[:-3]
        groups = []
        while len(leading) > 2:
            groups.insert(0, leading[-2:])
            leading = leading[:-2]
        if leading:
            groups.insert(0, leading)
        whole = ",".join(groups + [last_three])
    return f"{sign}₹{whole}.{fractional}"


def _month_year(period: dict) -> str:
    start = date.fromisoformat(period["from"])
    return start.strftime("%B %Y")


def _pct_label(pct_bp: int | None) -> str:
    if pct_bp is None:
        return "0.0"
    return f"{pct_bp / 100:.1f}"


def _fact(label: str, value_minor: int, count: int | None = None) -> dict:
    item = {"label": label, "value_minor": value_minor}
    if count is not None:
        item["count"] = count
    return item


def _standard_caveats(summary: dict, facts: list[dict]) -> list[str]:
    uncategorized_minor = int(summary.get("uncategorized_minor", 0))
    text = f"Computed from {summary.get('transactions_counted', 0)} spending transactions"
    if uncategorized_minor > 0:
        text += f"; {format_inr(uncategorized_minor)} is still uncategorized"
        if not any(fact["label"] == "Uncategorized" for fact in facts):
            uncategorized = next(
                (item for item in summary.get("by_category", []) if item.get("category") == "Uncategorized"),
                {"total_minor": uncategorized_minor, "count": 0},
            )
            facts.append(_fact("Uncategorized", uncategorized_minor, uncategorized.get("count", 0)))
    text += "."
    return [text]


def _unsupported(period: dict | None = None) -> dict:
    return {
        "answer": (
            "I can answer budget status, small transaction totals, top merchants, "
            "category totals, top spending categories, and total spending."
        ),
        "intent": "unsupported",
        "period": period or {},
        "facts": [],
        "caveats": [],
        "validation_status": "UNSUPPORTED",
        "engine": "rules",
    }


def _no_data(intent: str, period: dict) -> dict:
    return {
        "answer": "I don't have transactions for that period.",
        "intent": intent,
        "period": period,
        "facts": [],
        "caveats": [],
        "validation_status": "NO_DATA",
        "engine": "rules",
    }


def _category_from_question(question: str) -> str | None:
    normalized = question.casefold()
    for category in CATEGORIES:
        if category != "Uncategorized" and category.casefold() in normalized:
            return category
    return None


def _with_validation(answer: dict) -> dict:
    if validate_answer(answer):
        return answer
    if answer["facts"]:
        fact = answer["facts"][0]
        answer["answer"] = f"{fact['label']}: {format_inr(fact['value_minor'])}."
        answer["validation_status"] = "OK"
    return answer


def answer_question(question: str) -> dict:
    intent = detect_intent(question)
    if intent == "unsupported":
        return _unsupported()

    analytics = _load_analytics()
    reference_month = analytics.reference_month()
    date_from, date_to = detect_period(question, reference_month)
    period = {"from": date_from, "to": date_to}
    month_year = _month_year(period)

    if intent == "budget_status":
        status = budget_status(date_from[:7])
        facts: list[dict] = []
        if status["status"] == "NO_BUDGET":
            facts.append(_fact("Spent", status["spent_minor"]))
            answer = f"No budget is set for {month_year}. Spending so far is {format_inr(status['spent_minor'])}."
        else:
            facts.extend(
                [
                    _fact("Spent", status["spent_minor"]),
                    _fact("Budget limit", status["limit_minor"]),
                    _fact(
                        "Remaining" if status["remaining_minor"] >= 0 else "Over budget",
                        abs(status["remaining_minor"]),
                    ),
                ]
            )
            answer = (
                f"You have used {_pct_label(status['pct_bp'])}% of your {month_year} budget: "
                f"{format_inr(status['spent_minor'])} of {format_inr(status['limit_minor'])}. "
            )
            if status["remaining_minor"] >= 0:
                answer += f"{format_inr(status['remaining_minor'])} remaining."
            else:
                answer += f"You are {format_inr(abs(status['remaining_minor']))} over budget."
        return _with_validation(
            {
                "answer": answer,
                "intent": intent,
                "period": period,
                "facts": facts,
                "caveats": [],
                "validation_status": "OK",
                "engine": "rules",
            }
        )

    summary = analytics.summary(date_from, date_to)
    period = summary.get("period", period)
    month_year = _month_year(period)

    if int(summary.get("net_spend_minor", 0)) <= 0:
        return _no_data(intent, period)

    facts: list[dict] = []
    caveats: list[str] = []

    if intent == "top_categories":
        categories = summary.get("by_category", [])
        if not categories:
            return _no_data(intent, period)
        top_three = categories[:3]
        total_minor = int(summary["net_spend_minor"])
        facts.extend(
            _fact(item["category"], item["total_minor"], item.get("count"))
            for item in top_three
        )
        facts.append(_fact("Total spending", total_minor, summary.get("transactions_counted")))
        c1, c2, c3 = top_three
        answer = (
            f"Your top spending category for {month_year} is {c1['category']} at {format_inr(c1['total_minor'])} "
            f"({_pct_label(c1.get('pct_bp'))}% of {format_inr(total_minor)}). "
            f"Next: {c2['category']} {format_inr(c2['total_minor'])}, {c3['category']} {format_inr(c3['total_minor'])}."
        )
        caveats = _standard_caveats(summary, facts)

    elif intent == "small_txn_total":
        small = summary.get("small_payments", {})
        facts.append(_fact("Small payments", int(small.get("total_minor", 0)), int(small.get("count", 0))))
        facts.append(_fact("Small payment threshold", int(small.get("threshold_minor", 10000))))
        answer = (
            f"You made {small.get('count', 0)} small payments ({format_inr(int(small.get('threshold_minor', 10000)))} or less) "
            f"in {month_year}, totalling {format_inr(int(small.get('total_minor', 0)))}."
        )
        caveats = _standard_caveats(summary, facts)

    elif intent == "top_merchants":
        merchants = summary.get("top_merchants", [])[:3]
        if not merchants:
            return _no_data(intent, period)
        facts.extend(_fact(item["display_merchant"], item["total_minor"], item.get("count")) for item in merchants)
        m1, m2, m3 = merchants
        answer = (
            f"Your top merchants for {month_year}: {m1['display_merchant']} {format_inr(m1['total_minor'])}, "
            f"{m2['display_merchant']} {format_inr(m2['total_minor'])}, "
            f"{m3['display_merchant']} {format_inr(m3['total_minor'])}."
        )
        caveats = _standard_caveats(summary, facts)

    elif intent == "category_total":
        category = _category_from_question(question)
        category_row = next((item for item in summary.get("by_category", []) if item.get("category") == category), None)
        if not category_row:
            return _no_data(intent, period)
        facts.append(_fact(category, category_row["total_minor"], category_row.get("count")))
        answer = (
            f"You spent {format_inr(category_row['total_minor'])} on {category} in {month_year} "
            f"across {category_row.get('count', 0)} transactions."
        )
        caveats = _standard_caveats(summary, facts)

    elif intent == "total_spend":
        total_minor = int(summary.get("net_spend_minor", 0))
        income_minor = int(summary.get("income_minor", 0))
        facts.append(_fact("Total spending", total_minor, summary.get("transactions_counted")))
        if income_minor > 0:
            facts.append(_fact("Recorded income", income_minor))
        answer = f"Your total spending for {month_year} is {format_inr(total_minor)}."
        if income_minor > 0:
            answer += f" Recorded income was {format_inr(income_minor)}."
        caveats = _standard_caveats(summary, facts)

    else:
        return _unsupported(period)

    return _with_validation(
        {
            "answer": answer,
            "intent": intent,
            "period": period,
            "facts": facts,
            "caveats": caveats,
            "validation_status": "OK",
            "engine": "rules",
        }
    )


def validate_answer(answer: dict) -> bool:
    allowed = {format_inr(int(fact["value_minor"])) for fact in answer.get("facts", [])}
    text = " ".join([answer.get("answer", ""), *answer.get("caveats", [])])
    return all(match.group(0) in allowed for match in RUPEE_RE.finditer(text))
