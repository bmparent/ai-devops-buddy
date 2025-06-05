import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_devops_buddy.codex_runner import run

def test_run():
    result = run("example task")
    assert "pr" in result
