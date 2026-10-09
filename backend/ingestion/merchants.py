"""Merchant resolution and unknown-merchant review operations."""

from __future__ import annotations

from collections import defaultdict

from .dictionary import lookup


def _repo():
    from backend import repo  # type: ignore
    return repo


def resolve_merchant(parsed: dict) -> dict:
    if parsed["txn_type"] != "EXPENSE":
        return {
            "display_merchant": parsed.get("name_key") or parsed["counterparty_raw"],
            "merchant_source": "UNKNOWN", "category": "Uncategorized",
        }
    storage = _repo()
    if parsed.get("vpa"):
        alias = storage.get_alias("VPA", parsed["vpa"])
        if alias:
            return {"display_merchant": alias["display_merchant"], "merchant_source": "USER", "category": alias["category"]}
    if parsed.get("name_key"):
        alias = storage.get_alias("NAME", parsed["name_key"])
        if alias:
            return {"display_merchant": alias["display_merchant"], "merchant_source": "USER", "category": alias["category"]}
    found = lookup(parsed.get("name_key"))
    if found:
        display_merchant, category = found
        return {"display_merchant": display_merchant, "merchant_source": "DICTIONARY", "category": category}
    evidence = parsed.get("vpa") or parsed.get("name_key") or parsed["counterparty_raw"]
    return {"display_merchant": f"Unknown: {evidence}", "merchant_source": "UNKNOWN", "category": "Uncategorized"}


def review_queue() -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in _repo().list_transactions(txn_type="EXPENSE", merchant_source="UNKNOWN"):
        if row.get("vpa"):
            key = ("VPA", row["vpa"])
        elif row.get("name_key"):
            key = ("NAME", row["name_key"])
        else:
            continue
        grouped[key].append(row)
    items = []
    for (identifier_type, identifier_value), rows in grouped.items():
        raw_examples = list(dict.fromkeys(row["counterparty_raw"] for row in rows))[:3]
        items.append({
            "group_key": f"{identifier_type.lower()}:{identifier_value}",
            "identifier_type": identifier_type, "identifier_value": identifier_value,
            "raw_examples": raw_examples, "txn_count": len(rows),
            "total_minor": sum(row["amount_minor"] for row in rows),
        })
    return sorted(items, key=lambda item: (-item["total_minor"], item["group_key"]))


def resolve_group(group_key: str, display_name: str, category: str) -> dict:
    prefix, separator, identifier_value = group_key.partition(":")
    identifier_type = {"vpa": "VPA", "name": "NAME"}.get(prefix)
    if not separator or not identifier_type or not identifier_value:
        raise ValueError("group_key must start with vpa: or name:")
    storage = _repo()
    storage.upsert_alias(identifier_type, identifier_value, display_name, category)
    count = storage.update_transactions_for_identifier(identifier_type, identifier_value, display_name, category)
    return {"group_key": group_key, "display_merchant": display_name, "category": category, "transactions_updated": count}
