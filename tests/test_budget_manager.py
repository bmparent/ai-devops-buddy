from ai_buddy.budget_manager import BudgetManager


def test_choose_model() -> None:
    bm = BudgetManager()
    bm.record_tokens("gpt-4o", 90000)
    assert bm.choose_model(1) == "local-7b"
