from copy import deepcopy

import pytest

from backend import analytics, repo
from backend.models import format_inr, parse_date, rupees_to_minor, signed_spend_minor
from tests.sample_rows import ROWS_AFTER_ALIAS, ROWS_BEFORE_ALIAS

def load(rows):
    for row in rows:
        assert repo.insert_transaction(dict(row))

def test_money_and_date_helpers():
    assert rupees_to_minor("1,200.00") == 120000
    assert rupees_to_minor("Rs.20.5") == 2050
    assert rupees_to_minor("₹30") == 3000
    assert format_inr(591800) == "₹5,918.00"
    assert format_inr(12345678) == "₹1,23,456.78"
    assert parse_date("03/10/2026") == "2026-10-03"
    assert parse_date("03-10-2026") == "2026-10-03"
    assert parse_date("2026-10-03") == "2026-10-03"
    for value in ("0", "10000000", "1.001", "abc", "-1"):
        with pytest.raises(ValueError):
            rupees_to_minor(value)
    with pytest.raises(ValueError):
        parse_date("31/02/2026")
    with pytest.raises(ValueError):
        parse_date("01/01/2014")

def test_canonical_summary_and_totals(client):
    load(ROWS_AFTER_ALIAS)
    assert analytics.net_spend("2026-10-01", "2026-10-31") == 591800
    assert analytics.income_total("2026-10-01", "2026-10-31") == 825000
    result = analytics.summary("2026-10-01", "2026-10-31")
    assert result["net_spend_minor"] == 591800
    assert result["income_minor"] == 825000
    assert result["transactions_counted"] == 14
    assert [(x["category"], x["total_minor"], x["count"], x["pct_bp"]) for x in result["by_category"]] == [
        ("Transport", 142000, 2, 2399), ("Groceries", 135000, 1, 2281),
        ("Food", 105000, 7, 1774), ("Shopping", 79900, 1, 1350),
        ("Entertainment", 64900, 1, 1096), ("Bills", 50000, 1, 844),
        ("Uncategorized", 15000, 1, 253),
    ]
    assert result["top_merchants"] == [
        {"display_merchant": "BigBasket", "total_minor": 135000, "count": 1},
        {"display_merchant": "IRCTC", "total_minor": 120000, "count": 1},
        {"display_merchant": "Amazon Pay", "total_minor": 79900, "count": 1},
        {"display_merchant": "Netflix", "total_minor": 64900, "count": 1},
        {"display_merchant": "Swiggy", "total_minor": 54000, "count": 2},
    ]
    assert result["small_payments"] == {"threshold_minor": 10000, "count": 5, "total_minor": 22000}
    assert result["uncategorized_minor"] == 15000
    assert result["unknown_merchant_count"] == 1

def test_empty_database_returns_zeroes(client):
    result = analytics.summary("2026-10-01", "2026-10-31")
    assert result["net_spend_minor"] == result["income_minor"] == 0
    assert result["transactions_counted"] == 0
    assert result["by_category"] == result["top_merchants"] == []
    assert result["small_payments"] == {"threshold_minor": 10000, "count": 0, "total_minor": 0}

def test_income_and_transfer_not_spend_and_refund_is_negative(client):
    load(ROWS_AFTER_ALIAS)
    assert signed_spend_minor(ROWS_AFTER_ALIAS[9]) == 0
    assert signed_spend_minor(ROWS_AFTER_ALIAS[10]) == 0
    refund = deepcopy(ROWS_AFTER_ALIAS[0])
    refund.update(transaction_id="t_refund_test", dedup_key="ref:refund_test", date="2026-10-09",
                  amount_minor=5000, txn_type="REFUND", direction="CREDIT", upi_ref="refund_test")
    assert repo.insert_transaction(refund)
    assert analytics.net_spend("2026-10-01", "2026-10-31") == 586800

def test_dedup_alias_and_identifier_update(client):
    load(ROWS_BEFORE_ALIAS)
    assert repo.insert_transaction(dict(ROWS_BEFORE_ALIAS[0])) is False
    repo.upsert_alias("VPA", "q8812@ybl", "Tea stall", "Food")
    assert repo.get_alias("VPA", "q8812@ybl") == {
        "identifier_type": "VPA", "identifier_value": "q8812@ybl",
        "display_merchant": "Tea stall", "category": "Food",
    }
    assert repo.update_transactions_for_identifier("VPA", "q8812@ybl", "Tea stall", "Food") == 4
    affected = repo.list_transactions(category="Food")
    assert sum(1 for row in affected if row["display_merchant"] == "Tea stall") == 4
    assert all(row["counterparty_raw"] == "UPI-Q8812@ybl" or row["counterparty_raw"] == "q8812@ybl" for row in affected if row["display_merchant"] == "Tea stall")
    assert repo.list_aliases()[0]["display_merchant"] == "Tea stall"

def test_budget_repository_and_date_range(client):
    assert repo.get_budget("2026-10") is None
    repo.set_budget("2026-10", 650000)
    assert repo.get_budget("2026-10") == 650000
    load(ROWS_AFTER_ALIAS)
    assert analytics.net_spend("2026-10-01", "2026-10-02") == 87000
    assert len(repo.list_transactions(date_from="2026-10-03", date_to="2026-10-03")) == 2
