from backend import repo
from tests.sample_rows import ROWS_AFTER_ALIAS


def _load_rows():
    for row in ROWS_AFTER_ALIAS:
        assert repo.insert_transaction(dict(row))


def test_graph_analytics_custom_range_inclusive(client):
    _load_rows()
    response = client.get("/api/v1/analytics/graph", params={"from": "2026-10-01", "to": "2026-10-03"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == {"from": "2026-10-01", "to": "2026-10-03", "grouping": "day", "days": 3}
    assert payload["summary"]["net_spend_minor"] == 229000
    assert payload["summary"]["income_minor"] == 0
    assert payload["summary"]["spending_transaction_count"] == 6
    assert payload["summary"]["average_daily_net_spend_minor"] == 76333
    assert payload["summary"]["highest_merchant"]["display_merchant"] == "IRCTC"
    assert [point["date"] for point in payload["time_series"]] == ["2026-10-01", "2026-10-02", "2026-10-03"]
    assert [point["net_spend_minor"] for point in payload["time_series"]] == [47000, 40000, 142000]


def test_graph_analytics_full_fixture_aggregates(client):
    _load_rows()
    payload = client.get("/api/v1/analytics/graph", params={"from": "2026-10-01", "to": "2026-10-31"}).json()

    assert payload["summary"]["net_spend_minor"] == 591800
    assert payload["summary"]["income_minor"] == 825000
    assert payload["income_vs_expenditure"] == {
        "income_minor": 825000,
        "expense_minor": 591800,
        "refund_minor": 0,
        "net_spend_minor": 591800,
    }
    assert payload["category_breakdown"][0] == {
        "category": "Transport",
        "total_minor": 142000,
        "count": 2,
        "transactions": payload["category_breakdown"][0]["transactions"],
    }
    assert payload["merchant_breakdown"][0]["display_merchant"] == "BigBasket"
    assert payload["merchant_breakdown"][0]["average_minor"] == 135000
    assert payload["merchant_breakdown"][0]["share_bp"] == 2281
    assert all(row["txn_type"] != "TRANSFER_OUT" for row in payload["transactions"] if row["display_merchant"] != "SELF TRANSFER TO OWN A C")


def test_graph_analytics_empty_and_invalid_period(client):
    empty = client.get("/api/v1/analytics/graph", params={"from": "2026-09-01", "to": "2026-09-03"})
    assert empty.status_code == 200
    assert empty.json()["summary"]["net_spend_minor"] == 0
    assert empty.json()["time_series"] == []

    invalid = client.get("/api/v1/analytics/graph", params={"from": "2026-10-10", "to": "2026-10-01"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_graph_analytics_refunds_reduce_net_spend(client):
    row = dict(ROWS_AFTER_ALIAS[0])
    row.update(transaction_id="refund_1", dedup_key="refund:1", date="2026-10-02", txn_type="REFUND", amount_minor=5000)
    assert repo.insert_transaction(dict(ROWS_AFTER_ALIAS[0]))
    assert repo.insert_transaction(row)

    payload = client.get("/api/v1/analytics/graph", params={"from": "2026-10-01", "to": "2026-10-02"}).json()

    assert payload["summary"]["net_spend_minor"] == 40000
    assert payload["income_vs_expenditure"]["expense_minor"] == 45000
    assert payload["income_vs_expenditure"]["refund_minor"] == 5000
    assert payload["time_series"][1]["refund_minor"] == 5000
