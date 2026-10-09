"""Member 2 ingestion coverage; integration cases activate after M1/M4 land."""

import importlib.util

import pytest

from backend.ingestion.dedup import make_dedup_key, make_transaction_id
from backend.ingestion.dictionary import lookup
from backend.ingestion.normalize import derive_name_key, extract_vpa, normalize_name
from backend.ingestion.parsers import parse_csv_text, parse_paste_text


CSV_TEXT = """date,description,amount,direction,upi_ref
03/10/2026,UPI-UBER-uber@axisbank,220.00,DR,600000000005
04/10/2026,SELF TRANSFER-own@okaxis,1,DR,
"""
PASTE_TEXT = """Rs.20.00 debited from A/c XX1234 on 03-10-2026 to VPA q8812@ybl (Tea Stall) UPI Ref 600000000101.

Your OTP is 123456. Do not share it.

Rs.500.00 credited to A/c XX1234 on 04-10-2026 from VPA allowance@okaxis (Allowance) UPI Ref 600000000102.
"""

_SHARED_READY = importlib.util.find_spec("backend.models") is not None


def test_normalization_and_vpa_extraction() -> None:
    assert extract_vpa("UPI-RAJESH K-rajesh77@oksbi") == "rajesh77@oksbi"
    assert normalize_name("UPI-RAJESH K") == "RAJESH K"
    assert derive_name_key("UPI-SWIGGY-swiggy@icici", "swiggy@icici") == "SWIGGY"


def test_dictionary_order_and_deterministic_identity() -> None:
    assert lookup("SWIGGY INSTAMART") == ("Swiggy", "Food")
    key = make_dedup_key("600000000005", "2026-10-03", 22000, "DEBIT", "UPI-UBER-uber@axisbank")
    assert key == "ref:600000000005"
    assert make_transaction_id(key).startswith("t_")
    assert len(make_transaction_id(key)) == 14


def test_fingerprint_dedup_normalizes_counterparty() -> None:
    first = make_dedup_key(None, "2026-10-03", 22000, "DEBIT", "UPI-RAJESH K")
    second = make_dedup_key(None, "2026-10-03", 22000, "DEBIT", "RAJESH K")
    assert first == second


def test_csv_parser_preserves_raw_evidence_and_type_rules() -> None:
    parsed, rejected = parse_csv_text(CSV_TEXT)
    assert rejected == []
    assert parsed[0]["amount_minor"] == 22000
    assert parsed[0]["vpa"] == "uber@axisbank"
    assert parsed[0]["name_key"] == "UBER"
    assert parsed[1]["txn_type"] == "TRANSFER_OUT"


def test_paste_parser_ignores_non_transaction_blocks() -> None:
    parsed, rejected, ignored = parse_paste_text(PASTE_TEXT)
    assert rejected == []
    assert ignored == 1
    assert parsed[0]["counterparty_raw"] == "q8812@ybl (Tea Stall)"
    assert parsed[0]["txn_type"] == "EXPENSE"
    assert parsed[1]["txn_type"] == "INCOME"


@pytest.mark.skipif(not _SHARED_READY, reason="requires Member 1 models/repository and Member 4 sample data")
def test_sample_import_dedup_and_alias_journey(client) -> None:
    """T1/T3/T4 contract check, enabled once the team dependencies exist."""
    first = client.post("/api/v1/imports/sample")
    assert first.status_code == 200
    assert first.json() == {
        "source_type": "SAMPLE", "rows_found": 18, "imported": 17,
        "duplicates": 1, "rejected": 0, "ignored": 1,
        "unknown_merchants": 5, "rejected_rows": [],
    }
    second = client.post("/api/v1/imports/sample")
    assert second.json()["imported"] == 0
    assert second.json()["duplicates"] == 18
    resolved = client.post("/api/v1/merchants/resolve", json={
        "group_key": "vpa:q8812@ybl", "display_name": "Tea stall", "category": "Food",
    })
    assert resolved.status_code == 200
    assert resolved.json()["transactions_updated"] == 4


@pytest.mark.skipif(not _SHARED_READY, reason="requires Member 1 app and error handler")
def test_ingest_validation_contract(client) -> None:
    assert client.post("/api/v1/imports", json={"source_type": "PASTE", "text": ""}).status_code == 422
    assert client.post("/api/v1/imports", json={"source_type": "CSV", "text": "wrong,header"}).status_code == 422
    assert client.post("/api/v1/merchants/resolve", json={
        "group_key": "invalid", "display_name": "Tea", "category": "Food",
    }).status_code == 422
