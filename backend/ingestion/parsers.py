"""Pure parsers for the frozen CSV and pasted UPI-message formats."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .normalize import derive_name_key, extract_vpa, normalize_name


_CSV_HEADER = ["date", "description", "amount", "direction", "upi_ref"]
_CSV_ALIASES = {
    "date": {"date", "transaction date", "txn date", "trans date", "value date"},
    "description": {"description", "narration", "transaction details", "transaction description", "transaction remarks", "details", "remarks", "merchant", "payee", "counterparty", "counter party", "name", "particulars"},
    "amount": {"amount", "txn amount", "transaction amount"},
    "debit": {"debit", "debit amount", "debit amt", "withdrawal", "withdrawal amount", "withdrawal amt"},
    "credit": {"credit", "credit amount", "credit amt", "deposit", "deposit amount", "deposit amt"},
    "direction": {"direction", "dr cr", "dr/cr", "type", "transaction type"},
    "upi_ref": {"upi ref", "upi reference", "reference", "reference number", "transaction id", "txn id", "rrn"},
}
_MESSAGE_RE = re.compile(
    r"Rs\.\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s+"
    r"(?P<action>debited\s+from|credited\s+to)\s+A/c\s+\S+\s+on\s+"
    r"(?P<date>\d{2}-\d{2}-\d{4})\s+"
    r"(?P<relation>to|from)\s+VPA\s+(?P<vpa>[a-z0-9._]+@[a-z]+)"
    r"(?:\s*\((?P<name>[^)]+)\))?\s+UPI\s+Ref\s+(?P<upi_ref>\d{12})\.?",
    re.IGNORECASE | re.DOTALL,
)
_PLAIN_MESSAGE_RE = re.compile(
    r"Your\s+UPI\s+txn\s+of\s+Rs\.?\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s+"
    r"(?P<relation>to|from)\s+(?P<name>.+?)\s+on\s+"
    r"(?P<date>\d{2}-[A-Za-z]{3}-\d{4})\s+is\s+successful\.?\s+"
    r"UPI\s+Ref\s+(?P<upi_ref>\d{12})\.?",
    re.IGNORECASE | re.DOTALL,
)


def _rupees_to_minor(text: str) -> int:
    """Use M1's utility when available; preserve pure-parser progress before MP1."""
    try:
        from backend.models import rupees_to_minor  # type: ignore
    except ModuleNotFoundError:
        cleaned = re.sub(r"^(?:RS\.?|\u20b9)\s*", "", text.strip(), flags=re.IGNORECASE)
        try:
            value = Decimal(cleaned.replace(",", ""))
        except InvalidOperation as exc:
            raise ValueError("invalid amount") from exc
        if value <= 0 or value.as_tuple().exponent < -2 or value >= Decimal("10000000"):
            raise ValueError("amount must be > 0 and below 1 crore")
        return int(value * 100)
    return rupees_to_minor(text)


def _parse_date(text: str) -> str:
    try:
        from backend.models import parse_date  # type: ignore
    except ModuleNotFoundError:
        for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                value = datetime.strptime(text.strip(), pattern).date()
                if value.year < 2015:
                    break
                return value.isoformat()
            except ValueError:
                continue
        raise ValueError("invalid date")
    return parse_date(text)


def _transaction_type(direction: str, evidence: str) -> str:
    upper = evidence.upper()
    if direction == "CREDIT":
        return "REFUND" if "REFUND" in upper else "INCOME"
    return "TRANSFER_OUT" if "SELF TRANSFER" in upper or "OWN A/C" in upper else "EXPENSE"


def _parsed_row(
    *, date: str, description: str, amount: str, direction_code: str,
    upi_ref: str | None, source: str, raw_counterparty: str | None = None,
    vpa: str | None = None, name: str | None = None,
) -> dict:
    direction_map = {"DR": "DEBIT", "CR": "CREDIT", "DEBIT": "DEBIT", "CREDIT": "CREDIT"}
    direction = direction_map.get(direction_code.upper())
    if direction is None:
        raise ValueError("direction must be DR or CR")
    parsed_date = _parse_date(date)
    amount_minor = _rupees_to_minor(amount)
    vpa = vpa or extract_vpa(description)
    name_key = normalize_name(name) if name else derive_name_key(description, vpa)
    name_key = name_key or None
    txn_type = _transaction_type(direction, description)
    counterparty_raw = raw_counterparty or description
    return {
        "date": parsed_date, "amount_minor": amount_minor, "currency": "INR",
        "direction": direction, "txn_type": txn_type,
        "counterparty_raw": counterparty_raw, "vpa": vpa, "name_key": name_key,
        "upi_ref": upi_ref or None, "source": source,
    }


def parse_csv_text(text: str) -> tuple[list[dict], list[dict]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("CSV must include a header row")

    def normalize_header(value: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).split())

    columns = {}
    for original in reader.fieldnames:
        normalized = normalize_header(original or "")
        for canonical, aliases in _CSV_ALIASES.items():
            if normalized in {normalize_header(alias) for alias in aliases}:
                columns.setdefault(canonical, original)
                break
    if "date" not in columns or "description" not in columns:
        raise ValueError("CSV needs date and description columns")
    if "amount" not in columns and not ("debit" in columns or "credit" in columns):
        raise ValueError("CSV needs an amount, debit, or credit column")
    parsed, rejected = [], []
    for row_number, row in enumerate(reader, start=1):
        try:
            if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
                continue
            date_value = row.get(columns["date"], "")
            description = row.get(columns["description"], "")
            if not date_value or not date_value.strip():
                raise ValueError("date is required")
            if not description or not description.strip():
                raise ValueError("description is required")
            ref_column = columns.get("upi_ref")
            upi_ref = (row.get(ref_column, "") or "").strip() if ref_column else ""
            upi_ref = upi_ref or None
            if upi_ref and not re.fullmatch(r"\d{12}", upi_ref):
                normalized_ref_header = normalize_header(ref_column or "")
                if normalized_ref_header in {"upi ref", "upi reference", "rrn"}:
                    raise ValueError("upi_ref must be 12 digits")
                upi_ref = None
            direction_value = (row.get(columns.get("direction", ""), "") or "").strip().upper()
            amount_value = ""
            direction = {
                "DR": "DEBIT", "DR.": "DEBIT", "DEBITED": "DEBIT", "WITHDRAWAL": "DEBIT", "PAID": "DEBIT", "PAYMENT": "DEBIT",
                "CR": "CREDIT", "CR.": "CREDIT", "CREDITED": "CREDIT", "DEPOSIT": "CREDIT", "RECEIVED": "CREDIT",
            }.get(direction_value, direction_value)
            if "amount" in columns:
                amount_value = (row.get(columns["amount"], "") or "").strip()
            if not amount_value and ("debit" in columns or "credit" in columns):
                debit_value = (row.get(columns.get("debit", ""), "") or "").strip()
                credit_value = (row.get(columns.get("credit", ""), "") or "").strip()
                if debit_value:
                    amount_value, direction = debit_value, "DEBIT"
                elif credit_value:
                    amount_value, direction = credit_value, "CREDIT"
            if not amount_value:
                raise ValueError("amount is required")
            if not direction and amount_value.startswith("-"):
                direction, amount_value = "DEBIT", amount_value[1:].strip()
            elif not direction and re.search(r"\b(received|credited|deposit)\b", description, re.IGNORECASE):
                direction = "CREDIT"
            elif not direction and re.search(r"\b(paid|debited|withdrawal)\b", description, re.IGNORECASE):
                direction = "DEBIT"
            parsed.append(_parsed_row(
                date=date_value.strip(), description=description.strip(),
                amount=amount_value, direction_code=direction,
                upi_ref=upi_ref, source="CSV",
            ))
        except (ValueError, KeyError) as exc:
            rejected.append({"row": row_number, "reason": str(exc)})
    return parsed, rejected


def parse_paste_text(text: str) -> tuple[list[dict], list[dict], int]:
    parsed, rejected, ignored = [], [], 0
    blocks = [block.strip() for block in re.split(r"\r?\n\s*\r?\n", text.strip()) if block.strip()]
    for message_number, block in enumerate(blocks, start=1):
        match = _MESSAGE_RE.search(block)
        plain_format = False
        if not match:
            match = _PLAIN_MESSAGE_RE.search(block)
            plain_format = match is not None
        if not match:
            ignored += 1
            continue
        values = match.groupdict()
        try:
            if plain_format:
                merchant = values["name"].strip()
                direction = "DEBIT" if values["relation"].lower() == "to" else "CREDIT"
                parsed.append(_parsed_row(
                    date=values["date"], description=block, amount=values["amount"],
                    direction_code=direction, upi_ref=values["upi_ref"], source="PASTE",
                    raw_counterparty=merchant, name=merchant,
                ))
                continue
            vpa = values["vpa"].lower()
            name = (values.get("name") or "").strip() or None
            raw = f"{vpa} ({name})" if name else vpa
            direction = "DEBIT" if values["action"].lower().startswith("debited") else "CREDIT"
            parsed.append(_parsed_row(
                date=values["date"], description=block, amount=values["amount"],
                direction_code=direction, upi_ref=values["upi_ref"], source="PASTE",
                raw_counterparty=raw, vpa=vpa, name=name,
            ))
        except ValueError as exc:
            rejected.append({"row": message_number, "reason": str(exc)})
    return parsed, rejected, ignored
