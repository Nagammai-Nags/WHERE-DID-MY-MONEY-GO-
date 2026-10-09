"""Ingestion orchestration from raw text to canonical stored transactions."""

from __future__ import annotations

from pathlib import Path

from .dedup import make_dedup_key, make_transaction_id
from .merchants import resolve_merchant
from .parsers import parse_csv_text, parse_paste_text


def _api_error(message: str):
    from backend.models import ApiError  # type: ignore
    return ApiError(422, "VALIDATION_ERROR", message)


def _repo():
    from backend import repo  # type: ignore
    return repo


def _empty_result(source_type: str) -> dict:
    return {"source_type": source_type, "rows_found": 0, "imported": 0, "duplicates": 0,
            "rejected": 0, "ignored": 0, "unknown_merchants": 0, "rejected_rows": []}


def import_text(source_type: str, text: str) -> dict:
    if source_type not in {"CSV", "PASTE"}:
        raise _api_error("source_type must be CSV or PASTE")
    if not isinstance(text, str) or not text.strip():
        raise _api_error("text must not be empty")
    try:
        if source_type == "CSV":
            parsed, rejected = parse_csv_text(text)
            ignored = 0
        else:
            parsed, rejected, ignored = parse_paste_text(text)
    except ValueError as exc:
        raise _api_error(str(exc)) from exc
    result = _empty_result(source_type)
    result.update({"rejected": len(rejected), "ignored": ignored, "rejected_rows": rejected})
    for parsed_row in parsed:
        canonical = dict(parsed_row)
        canonical.update(resolve_merchant(parsed_row))
        canonical["dedup_key"] = make_dedup_key(
            canonical.get("upi_ref"), canonical["date"], canonical["amount_minor"],
            canonical["direction"], canonical["counterparty_raw"],
        )
        canonical["transaction_id"] = make_transaction_id(canonical["dedup_key"])
        if _repo().insert_transaction(canonical):
            result["imported"] += 1
            if canonical["txn_type"] == "EXPENSE" and canonical["merchant_source"] == "UNKNOWN":
                result["unknown_merchants"] += 1
        else:
            result["duplicates"] += 1
    result["rows_found"] = result["imported"] + result["duplicates"] + result["rejected"]
    return result


def import_sample() -> dict:
    root = Path(__file__).resolve().parents[2]
    try:
        csv_text = (root / "data" / "sample_transactions.csv").read_text(encoding="utf-8")
        messages_text = (root / "data" / "sample_messages.txt").read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError("sample files are unavailable") from exc
    csv_result, message_result = import_text("CSV", csv_text), import_text("PASTE", messages_text)
    result = _empty_result("SAMPLE")
    for key in ("rows_found", "imported", "duplicates", "rejected", "ignored", "unknown_merchants"):
        result[key] = csv_result[key] + message_result[key]
    result["rejected_rows"] = csv_result["rejected_rows"] + message_result["rejected_rows"]
    return result
