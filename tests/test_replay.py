from ai_buddy.replay import replay_task
from pathlib import Path
import os
import json


def test_replay_match(tmp_path: Path) -> None:
    base = tmp_path / "tasks"
    base.mkdir(parents=True)
    file = base / "1.json"
    data = {"result": 1}
    file.write_text(json.dumps(data))
    os.environ["REPLAY_BASE"] = str(base)
    assert replay_task("1") == "MATCH"
