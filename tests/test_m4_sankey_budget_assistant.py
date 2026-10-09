from pathlib import Path

from backend.budget.budget import compute_status
from backend.budget.api_budget import _validate_limit_minor, _validate_optional_month
from backend.assistant.assistant import answer_question, validate_answer
import backend.assistant.assistant as assistant_module
from backend.sankey import build_sankey


ROWS_AFTER_ALIAS = [
    {"date": "2026-10-01", "amount_minor": 45000, "txn_type": "EXPENSE", "display_merchant": "Swiggy", "category": "Food"},
    {"date": "2026-10-01", "amount_minor": 2000, "txn_type": "EXPENSE", "display_merchant": "Tea stall", "category": "Food"},
    {"date": "2026-10-02", "amount_minor": 38000, "txn_type": "EXPENSE", "display_merchant": "Zomato", "category": "Food"},
    {"date": "2026-10-02", "amount_minor": 2000, "txn_type": "EXPENSE", "display_merchant": "Tea stall", "category": "Food"},
    {"date": "2026-10-03", "amount_minor": 22000, "txn_type": "EXPENSE", "display_merchant": "Uber", "category": "Transport"},
    {"date": "2026-10-03", "amount_minor": 120000, "txn_type": "EXPENSE", "display_merchant": "IRCTC", "category": "Transport"},
    {"date": "2026-10-04", "amount_minor": 64900, "txn_type": "EXPENSE", "display_merchant": "Netflix", "category": "Entertainment"},
    {"date": "2026-10-04", "amount_minor": 15000, "txn_type": "EXPENSE", "display_merchant": "Unknown: rajesh77@oksbi", "category": "Uncategorized"},
    {"date": "2026-10-05", "amount_minor": 135000, "txn_type": "EXPENSE", "display_merchant": "BigBasket", "category": "Groceries"},
    {"date": "2026-10-05", "amount_minor": 800000, "txn_type": "INCOME", "display_merchant": "NEFT ALLOWANCE FROM PARENTS", "category": "Uncategorized"},
    {"date": "2026-10-06", "amount_minor": 200000, "txn_type": "TRANSFER_OUT", "display_merchant": "SELF TRANSFER TO OWN A C", "category": "Uncategorized"},
    {"date": "2026-10-06", "amount_minor": 3000, "txn_type": "EXPENSE", "display_merchant": "Tea stall", "category": "Food"},
    {"date": "2026-10-07", "amount_minor": 79900, "txn_type": "EXPENSE", "display_merchant": "Amazon Pay", "category": "Shopping"},
    {"date": "2026-10-07", "amount_minor": 9000, "txn_type": "EXPENSE", "display_merchant": "Swiggy", "category": "Food"},
    {"date": "2026-10-08", "amount_minor": 6000, "txn_type": "EXPENSE", "display_merchant": "Tea stall", "category": "Food"},
    {"date": "2026-10-08", "amount_minor": 50000, "txn_type": "EXPENSE", "display_merchant": "Jio", "category": "Bills"},
    {"date": "2026-10-08", "amount_minor": 25000, "txn_type": "INCOME", "display_merchant": "AMIT S", "category": "Uncategorized"},
]


EXPECTED_STATE_B_LINKS = {
    ("root", "cat:Transport"): 142000,
    ("root", "cat:Groceries"): 135000,
    ("root", "cat:Food"): 105000,
    ("root", "cat:Shopping"): 79900,
    ("root", "cat:Entertainment"): 64900,
    ("root", "cat:Bills"): 50000,
    ("root", "cat:Uncategorized"): 15000,
    ("root", "unspent"): 233200,
    ("cat:Transport", "merchant:Transport:IRCTC"): 120000,
    ("cat:Transport", "merchant:Transport:Uber"): 22000,
    ("cat:Groceries", "merchant:Groceries:BigBasket"): 135000,
    ("cat:Food", "merchant:Food:Swiggy"): 45000,
    ("cat:Food", "merchant:Food:Zomato"): 38000,
    ("cat:Food", "small:Food"): 22000,
    ("cat:Shopping", "merchant:Shopping:Amazon Pay"): 79900,
    ("cat:Entertainment", "merchant:Entertainment:Netflix"): 64900,
    ("cat:Bills", "merchant:Bills:Jio"): 50000,
    ("cat:Uncategorized", "merchant:Uncategorized:Unknown: rajesh77@oksbi"): 15000,
}


SUMMARY_STATE_B = {
    "period": {"from": "2026-10-01", "to": "2026-10-31"},
    "net_spend_minor": 591800,
    "income_minor": 825000,
    "transactions_counted": 14,
    "by_category": [
        {"category": "Transport", "total_minor": 142000, "count": 2, "pct_bp": 2399},
        {"category": "Groceries", "total_minor": 135000, "count": 1, "pct_bp": 2281},
        {"category": "Food", "total_minor": 105000, "count": 7, "pct_bp": 1774},
        {"category": "Shopping", "total_minor": 79900, "count": 1, "pct_bp": 1350},
        {"category": "Entertainment", "total_minor": 64900, "count": 1, "pct_bp": 1096},
        {"category": "Bills", "total_minor": 50000, "count": 1, "pct_bp": 844},
        {"category": "Uncategorized", "total_minor": 15000, "count": 1, "pct_bp": 253},
    ],
    "top_merchants": [
        {"display_merchant": "BigBasket", "total_minor": 135000, "count": 1},
        {"display_merchant": "IRCTC", "total_minor": 120000, "count": 1},
        {"display_merchant": "Amazon Pay", "total_minor": 79900, "count": 1},
        {"display_merchant": "Netflix", "total_minor": 64900, "count": 1},
        {"display_merchant": "Swiggy", "total_minor": 54000, "count": 2},
    ],
    "small_payments": {"threshold_minor": 10000, "count": 5, "total_minor": 22000},
    "uncategorized_minor": 15000,
    "unknown_merchant_count": 1,
}


class FakeAnalytics:
    calls = 0

    @staticmethod
    def reference_month():
        return "2026-10"

    @classmethod
    def summary(cls, date_from, date_to):
        cls.calls += 1
        assert (date_from, date_to) == ("2026-10-01", "2026-10-31")
        return SUMMARY_STATE_B


def _patch_assistant_dependencies(monkeypatch):
    FakeAnalytics.calls = 0
    monkeypatch.setattr(assistant_module, "_load_analytics", lambda: FakeAnalytics)
    monkeypatch.setattr(
        assistant_module,
        "budget_status",
        lambda month=None: {
            "month": "2026-10",
            "limit_minor": 650000,
            "spent_minor": 591800,
            "remaining_minor": 58200,
            "pct_bp": 9104,
            "status": "WARNING",
        },
    )


def test_compute_status_budget_cases_from_spec():
    spent_minor = 591800

    assert compute_status(None, spent_minor) == {
        "limit_minor": None,
        "spent_minor": 591800,
        "remaining_minor": None,
        "pct_bp": None,
        "status": "NO_BUDGET",
    }
    assert compute_status(1000000, spent_minor) == {
        "limit_minor": 1000000,
        "spent_minor": 591800,
        "remaining_minor": 408200,
        "pct_bp": 5918,
        "status": "OK",
    }
    assert compute_status(750000, spent_minor) == {
        "limit_minor": 750000,
        "spent_minor": 591800,
        "remaining_minor": 158200,
        "pct_bp": 7890,
        "status": "OK",
    }
    assert compute_status(650000, spent_minor) == {
        "limit_minor": 650000,
        "spent_minor": 591800,
        "remaining_minor": 58200,
        "pct_bp": 9104,
        "status": "WARNING",
    }
    assert compute_status(500000, spent_minor) == {
        "limit_minor": 500000,
        "spent_minor": 591800,
        "remaining_minor": -91800,
        "pct_bp": 11836,
        "status": "EXCEEDED",
    }


def test_budget_validation_helpers():
    assert _validate_optional_month(None) is None
    assert _validate_optional_month("2026-10") == "2026-10"
    assert _validate_limit_minor(100) == 100
    assert _validate_limit_minor(650000) == 650000


def test_budget_validation_rejects_bad_values():
    for bad_month in ("2026-1", "2026-13", "october", 202610):
        try:
            _validate_optional_month(bad_month)
        except Exception as exc:
            assert getattr(exc, "status", None) == 422
            assert getattr(exc, "code", None) == "VALIDATION_ERROR"
        else:
            raise AssertionError(f"accepted bad month {bad_month!r}")

    for bad_limit in (None, 0, 99, 12.5, True, "650000"):
        try:
            _validate_limit_minor(bad_limit)
        except Exception as exc:
            assert getattr(exc, "status", None) == 422
            assert getattr(exc, "code", None) == "VALIDATION_ERROR"
        else:
            raise AssertionError(f"accepted bad limit {bad_limit!r}")


def test_build_sankey_matches_state_b_expected_graph():
    payload = build_sankey(ROWS_AFTER_ALIAS, "2026-10-01", "2026-10-31")

    links = {
        (link["source"], link["target"]): link["value_minor"]
        for link in payload["links"]
    }
    nodes = {node["id"]: node for node in payload["nodes"]}

    assert links == EXPECTED_STATE_B_LINKS
    assert len(nodes) == 19
    assert len(payload["links"]) == 18
    assert payload["meta"] == {
        "period": {"from": "2026-10-01", "to": "2026-10-31"},
        "root_kind": "INCOME",
        "net_spend_minor": 591800,
        "income_minor": 825000,
        "overspent_minor": 0,
        "small_threshold_minor": 10000,
        "refund_excess_minor": 0,
        "integrity_ok": True,
    }
    assert nodes["small:Food"]["count"] == 5
    assert "merchant:Food:Tea stall" not in nodes


def test_build_sankey_uses_spend_root_when_income_is_missing():
    expense_only = [row for row in ROWS_AFTER_ALIAS if row["txn_type"] != "INCOME"]

    payload = build_sankey(expense_only, "2026-10-01", "2026-10-31")
    nodes = {node["id"]: node for node in payload["nodes"]}

    assert nodes["root"] == {"id": "root", "name": "Total spending", "kind": "ROOT_SPEND"}
    assert "unspent" not in nodes
    assert payload["meta"]["root_kind"] == "SPEND"
    assert payload["meta"]["income_minor"] == 0
    assert payload["meta"]["integrity_ok"] is True


def test_assistant_supported_questions_use_computed_facts(monkeypatch):
    _patch_assistant_dependencies(monkeypatch)

    cases = [
        (
            "Where did most of my money go this month?",
            "top_categories",
            "Your top spending category for October 2026 is Transport at ₹1,420.00 (24.0% of ₹5,918.00). Next: Groceries ₹1,350.00, Food ₹1,050.00.",
        ),
        (
            "How much did I spend on small transactions?",
            "small_txn_total",
            "You made 5 small payments (₹100.00 or less) in October 2026, totalling ₹220.00.",
        ),
        (
            "Which merchants did I spend the most at?",
            "top_merchants",
            "Your top merchants for October 2026: BigBasket ₹1,350.00, IRCTC ₹1,200.00, Amazon Pay ₹799.00.",
        ),
        (
            "How much did I spend on Food?",
            "category_total",
            "You spent ₹1,050.00 on Food in October 2026 across 7 transactions.",
        ),
        (
            "What is my total spending?",
            "total_spend",
            "Your total spending for October 2026 is ₹5,918.00. Recorded income was ₹8,250.00.",
        ),
        (
            "How is my budget?",
            "budget_status",
            "You have used 91.0% of your October 2026 budget: ₹5,918.00 of ₹6,500.00. ₹582.00 remaining.",
        ),
    ]

    for question, intent, expected_answer in cases:
        result = answer_question(question)
        assert result["intent"] == intent
        assert result["answer"] == expected_answer
        assert result["validation_status"] == "OK"
        assert result["engine"] == "rules"
        assert validate_answer(result)


def test_assistant_top_category_first_fact_matches_summary(monkeypatch):
    _patch_assistant_dependencies(monkeypatch)

    result = answer_question("Where did most of my money go this month?")

    assert result["facts"][0] == {"label": "Transport", "value_minor": 142000, "count": 2}
    assert result["caveats"] == ["Computed from 14 spending transactions; ₹150.00 is still uncategorized."]


def test_assistant_unsupported_does_not_call_analytics(monkeypatch):
    _patch_assistant_dependencies(monkeypatch)

    result = answer_question("Should I invest in mutual funds?")

    assert result["intent"] == "unsupported"
    assert result["validation_status"] == "UNSUPPORTED"
    assert result["facts"] == []
    assert "₹" not in result["answer"]
    assert FakeAnalytics.calls == 0


def test_validate_answer_rejects_unbacked_rupee_amount(monkeypatch):
    _patch_assistant_dependencies(monkeypatch)
    result = answer_question("Where did most of my money go this month?")

    tampered = {**result, "answer": result["answer"] + " Also ₹999.00."}

    assert validate_answer(result)
    assert not validate_answer(tampered)


def test_member4_frontend_integration_globals_exist():
    root = Path(__file__).resolve().parents[1]
    budget_js = (root / "frontend" / "budget.js").read_text()
    assistant_js = (root / "frontend" / "assistant.js").read_text()

    assert "window.WDMMG_BudgetPanel = { mount, refresh };" in budget_js
    assert 'apiClient().get(`/budget${query}`)' in budget_js
    assert 'apiClient().put("/budget", payload)' in budget_js

    assert "window.WDMMG_AssistantPanel = { mount };" in assistant_js
    assert 'apiClient().post("/assistant/query", { question })' in assistant_js
    assert "Where did most of my money go this month?" in assistant_js


def test_member4_backend_router_exports_are_available():
    from backend.assistant import api_assistant
    from backend.budget import api_budget
    import backend.sankey as sankey_api

    assert hasattr(api_assistant, "router")
    assert hasattr(api_budget, "router")
    assert hasattr(sankey_api, "router")
    assert callable(api_assistant.query_assistant)
    assert callable(api_budget.get_budget)
    assert callable(api_budget.put_budget)
    assert callable(sankey_api.get_sankey)
