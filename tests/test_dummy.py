import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import ai_buddy.orchestrator as orch


def test_import() -> None:
    assert hasattr(orch, "Orchestrator")
