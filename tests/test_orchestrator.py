from ai_buddy.orchestrator import Orchestrator


def test_plugins() -> None:
    orch = Orchestrator()
    assert "demo" in orch.skills
