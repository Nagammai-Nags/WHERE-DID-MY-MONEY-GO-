"""Core journey available before teammate routers are integrated."""
from backend import repo
from tests.sample_rows import ROWS_AFTER_ALIAS

def test_core_data_to_summary_journey(client):
    assert client.get("/api/v1/healthz").json()["status"] == "ok"
    assert client.get("/api/v1/analytics/summary").json()["net_spend_minor"] == 0
    for row in ROWS_AFTER_ALIAS:
        assert repo.insert_transaction(dict(row))
    response = client.get("/api/v1/analytics/summary", params={"from": "2026-10-01", "to": "2026-10-31"})
    assert response.status_code == 200
    assert response.json()["net_spend_minor"] == 591800
    assert response.json()["income_minor"] == 825000
    txns = client.get("/api/v1/transactions", params={"category": "Food"}).json()
    assert txns["count"] == 7
    assert client.post("/api/v1/dev/reset").status_code == 200
    assert client.get("/api/v1/analytics/summary", params={"from": "2026-10-01", "to": "2026-10-31"}).json()["net_spend_minor"] == 0
