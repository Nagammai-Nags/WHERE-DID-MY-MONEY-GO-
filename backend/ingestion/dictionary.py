"""Small deterministic merchant dictionary for the prototype."""

from __future__ import annotations


DICTIONARY: list[tuple[str, str, str]] = [
    ("SWIGGY", "Swiggy", "Food"),
    ("ZOMATO", "Zomato", "Food"),
    ("UBER", "Uber", "Transport"),
    ("IRCTC", "IRCTC", "Transport"),
    ("NETFLIX", "Netflix", "Entertainment"),
    ("BIGBASKET", "BigBasket", "Groceries"),
    ("AMAZON PAY", "Amazon Pay", "Shopping"),
    ("JIO", "Jio", "Bills"),
]


def lookup(name_key: str | None) -> tuple[str, str] | None:
    if not name_key:
        return None
    for key, display_name, category in DICTIONARY:
        if key in name_key:
            return display_name, category
    return None
