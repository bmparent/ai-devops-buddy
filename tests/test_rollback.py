from ai_buddy.rollback import check_and_rollback


def test_rollback_trigger() -> None:
    assert check_and_rollback(0.03) == "ROLLBACK"
    assert check_and_rollback(0.0) == "OK"
