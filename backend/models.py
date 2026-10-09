"""Shared transaction contract and deterministic money/date helpers."""
from __future__ import annotations
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Mapping, TypedDict

CATEGORIES = ["Food", "Transport", "Groceries", "Entertainment", "Shopping", "Bills", "Education", "Uncategorized"]
SMALL_THRESHOLD_MINOR = 10000
TXN_TYPES = ("EXPENSE", "INCOME", "REFUND", "TRANSFER_OUT", "TRANSFER_IN", "IGNORED")

class Transaction(TypedDict):
    transaction_id: str
    date: str
    amount_minor: int
    currency: str
    direction: str
    txn_type: str
    counterparty_raw: str
    vpa: str | None
    name_key: str | None
    display_merchant: str
    merchant_source: str
    category: str
    upi_ref: str | None
    source: str
    dedup_key: str

class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message

def rupees_to_minor(text: str) -> int:
    value = text.strip().replace(",", "")
    value = re.sub(r"^(?:Rs\.?|₹)\s*", "", value, flags=re.IGNORECASE)
    try:
        amount = Decimal(value)
    except (InvalidOperation, AttributeError):
        raise ValueError("amount must be a valid rupee value") from None
    if not amount.is_finite() or amount <= 0 or amount >= Decimal("10000000"):
        raise ValueError("amount must be greater than 0 and less than ₹1 crore")
    if amount.as_tuple().exponent < -2:
        raise ValueError("amount must have no more than 2 decimal places")
    minor = amount * 100
    if minor != minor.to_integral_value():
        raise ValueError("amount must have no more than 2 decimal places")
    return int(minor)

def format_inr(minor: int) -> str:
    if isinstance(minor, bool) or not isinstance(minor, int):
        raise TypeError("minor must be an integer")
    sign = "-" if minor < 0 else ""
    rupees, paise = divmod(abs(minor), 100)
    digits = str(rupees)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while head:
            groups.append(head[-2:])
            head = head[:-2]
        digits = ",".join(reversed(groups)) + "," + tail
    return f"{sign}₹{digits}.{paise:02d}"

def parse_date(text: str) -> str:
    value = text.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            if parsed.year < 2015:
                raise ValueError("date year must be 2015 or later")
            return parsed.isoformat()
        except ValueError as exc:
            if "2015" in str(exc):
                raise
    raise ValueError("date must be dd/mm/yyyy, dd-mm-yyyy, or yyyy-mm-dd")

def signed_spend_minor(t: Mapping[str, object]) -> int:
    amount = int(t["amount_minor"])
    if t["txn_type"] == "EXPENSE":
        return amount
    if t["txn_type"] == "REFUND":
        return -amount
    return 0
