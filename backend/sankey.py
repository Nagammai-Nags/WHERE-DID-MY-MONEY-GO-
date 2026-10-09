from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

try:
    from fastapi import APIRouter, Query
except ImportError:  # pragma: no cover - lets pure tests run before deps land.
    APIRouter = None
    Query = None

try:
    from backend.models import ApiError, signed_spend_minor
except ImportError:  # pragma: no cover - replaced by M1's implementation.
    class ApiError(Exception):
        def __init__(self, status: int, code: str, message: str):
            self.status = status
            self.code = code
            self.message = message
            super().__init__(message)

    def signed_spend_minor(t: Mapping[str, Any]) -> int:
        if t.get("txn_type") == "EXPENSE":
            return int(t.get("amount_minor", 0))
        if t.get("txn_type") == "REFUND":
            return -int(t.get("amount_minor", 0))
        return 0


router = APIRouter() if APIRouter else None


def _in_period(row: Mapping[str, Any], date_from: str, date_to: str) -> bool:
    row_date = str(row.get("date", ""))
    return date_from <= row_date <= date_to


def _add_node(nodes_by_id: dict[str, dict], node_id: str, name: str, kind: str, **extra: Any) -> None:
    if node_id not in nodes_by_id:
        nodes_by_id[node_id] = {"id": node_id, "name": name, "kind": kind, **extra}
    else:
        nodes_by_id[node_id].update(extra)


def _integrity_ok(nodes: Iterable[dict], links: Iterable[dict]) -> bool:
    node_ids = {node["id"] for node in nodes}
    inflow: dict[str, int] = defaultdict(int)
    outflow: dict[str, int] = defaultdict(int)

    for link in links:
        value = link.get("value_minor")
        source = link.get("source")
        target = link.get("target")
        if not isinstance(value, int) or value <= 0:
            return False
        if source not in node_ids or target not in node_ids:
            return False
        outflow[source] += value
        inflow[target] += value

    for node_id in node_ids:
        if node_id == "root":
            continue
        if node_id == "unspent" or not outflow[node_id]:
            continue
        if inflow[node_id] != outflow[node_id]:
            return False

    return True


def build_sankey(
    rows: list[dict],
    date_from: str,
    date_to: str,
    small_threshold_minor: int = 10000,
) -> dict:
    nodes_by_id: dict[str, dict] = {}
    links: list[dict] = []
    category_totals: dict[str, int] = defaultdict(int)
    merchant_totals: dict[tuple[str, str], int] = defaultdict(int)
    small_totals: dict[str, int] = defaultdict(int)
    small_counts: dict[str, int] = defaultdict(int)
    income_minor = 0
    raw_net_spend_minor = 0

    for row in rows:
        if not _in_period(row, date_from, date_to):
            continue

        if row.get("txn_type") == "INCOME":
            income_minor += int(row.get("amount_minor", 0))

        signed_amount = signed_spend_minor(row)
        raw_net_spend_minor += signed_amount
        if signed_amount == 0:
            continue

        category = str(row.get("category") or "Uncategorized")
        category_totals[category] += signed_amount

        if row.get("txn_type") == "EXPENSE" and int(row.get("amount_minor", 0)) <= small_threshold_minor:
            small_totals[category] += int(row["amount_minor"])
            small_counts[category] += 1
        else:
            merchant = str(row.get("display_merchant") or "Unknown")
            merchant_totals[(category, merchant)] += signed_amount

    positive_category_totals = {
        category: total for category, total in category_totals.items() if total > 0
    }
    category_links_total = sum(positive_category_totals.values())
    net_spend_minor = max(raw_net_spend_minor, 0)
    refund_excess_minor = max(category_links_total - net_spend_minor, 0)

    if income_minor > 0:
        root_kind = "INCOME"
        root_name = "Income"
    else:
        root_kind = "SPEND"
        root_name = "Total spending"
    _add_node(nodes_by_id, "root", root_name, f"ROOT_{root_kind}")

    for category, total in sorted(positive_category_totals.items(), key=lambda item: (-item[1], item[0])):
        category_id = f"cat:{category}"
        _add_node(nodes_by_id, category_id, category, "CATEGORY")
        links.append({"source": "root", "target": category_id, "value_minor": total})

        merchant_items = [
            ((merchant_category, merchant), value)
            for (merchant_category, merchant), value in merchant_totals.items()
            if merchant_category == category and value > 0
        ]
        for (_, merchant), value in sorted(merchant_items, key=lambda item: (-item[1], item[0][1])):
            merchant_id = f"merchant:{category}:{merchant}"
            _add_node(nodes_by_id, merchant_id, merchant, "MERCHANT")
            links.append({"source": category_id, "target": merchant_id, "value_minor": value})

        small_total = small_totals.get(category, 0)
        if small_total > 0:
            small_id = f"small:{category}"
            _add_node(
                nodes_by_id,
                small_id,
                "Small payments",
                "SMALL",
                count=small_counts[category],
                threshold_minor=small_threshold_minor,
            )
            links.append({"source": category_id, "target": small_id, "value_minor": small_total})

    overspent_minor = 0
    if income_minor > 0:
        if income_minor > category_links_total:
            unspent_minor = income_minor - category_links_total
            _add_node(nodes_by_id, "unspent", "Not spent in this period", "UNSPENT")
            links.append({"source": "root", "target": "unspent", "value_minor": unspent_minor})
        elif category_links_total > income_minor:
            overspent_minor = category_links_total - income_minor

    nodes = list(nodes_by_id.values())
    return {
        "nodes": nodes,
        "links": links,
        "meta": {
            "period": {"from": date_from, "to": date_to},
            "root_kind": root_kind,
            "net_spend_minor": net_spend_minor,
            "income_minor": income_minor,
            "overspent_minor": overspent_minor,
            "small_threshold_minor": small_threshold_minor,
            "refund_excess_minor": refund_excess_minor,
            "integrity_ok": _integrity_ok(nodes, links),
        },
    }


def get_sankey(
    from_: str | None = Query(None, alias="from") if Query else None,
    to: str | None = None,
    small_threshold_minor: int = Query(10000) if Query else 10000,
) -> dict:
    if small_threshold_minor < 1:
        raise ApiError(422, "VALIDATION_ERROR", "small_threshold_minor must be positive")

    from backend import analytics, repo

    if from_ is None or to is None:
        month = analytics.reference_month()
        default_from, default_to = analytics.month_bounds(month)
        from_ = from_ or default_from
        to = to or default_to
    if from_ > to:
        raise ApiError(422, "VALIDATION_ERROR", "from must be before or equal to to")

    rows = repo.list_transactions(from_, to)
    return build_sankey(rows, from_, to, small_threshold_minor)


if router:
    router.add_api_route("/analytics/sankey", get_sankey, methods=["GET"])
