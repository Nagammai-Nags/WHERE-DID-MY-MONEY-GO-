from tests.sample_rows import ROWS_AFTER_ALIAS
from backend import repo

SUMMARY_KEYS = {"period", "net_spend_minor", "income_minor", "transactions_counted", "by_category",
                "top_merchants", "small_payments", "uncategorized_minor", "unknown_merchant_count"}
TRANSACTION_KEYS = {"transaction_id", "date", "amount_minor", "currency", "direction", "txn_type",
                    "counterparty_raw", "vpa", "name_key", "display_merchant", "merchant_source",
                    "category", "upi_ref", "source", "dedup_key"}

def test_core_response_contracts(client):
    assert client.get("/api/v1/healthz").json() == {"status": "ok"}
    assert client.get("/api/v1/categories").json() == {"items": ["Food", "Transport", "Groceries", "Entertainment", "Shopping", "Bills", "Education", "Uncategorized"]}
    summary = client.get("/api/v1/analytics/summary", params={"from": "2026-10-01", "to": "2026-10-31"}).json()
    assert set(summary) == SUMMARY_KEYS
    assert summary["period"] == {"from": "2026-10-01", "to": "2026-10-31"}
    assert client.get("/api/v1/transactions").json() == {"items": [], "count": 0}
    for row in ROWS_AFTER_ALIAS:
        repo.insert_transaction(dict(row))
    payload = client.get("/api/v1/transactions", params={"limit": 1}).json()
    assert set(payload) == {"items", "count"} and payload["count"] == 1
    assert set(payload["items"][0]) == TRANSACTION_KEYS
    assert client.post("/api/v1/dev/reset").json() == {"status": "ok"}

def test_invalid_date_responses_use_shared_error_envelope(client):
    for params in ({"from": "bad"}, {"from": "2026-10-10", "to": "2026-10-01"}):
        response = client.get("/api/v1/analytics/summary", params=params)
        assert response.status_code == 422
        assert set(response.json()) == {"error"}
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
