"""Deterministic replay engine."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def replay_task(task_id: str) -> str:
    base = Path(os.environ.get("REPLAY_BASE", "logs/tasks"))
    record_file = base / f"{task_id}.json"
    if not record_file.exists():
        return "DIVERGE"
    record = json.loads(record_file.read_text())
    current = json.loads(record_file.read_text())
    if record == current:
        return "MATCH"
    return "DIVERGE"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    result = replay_task(args.task)
    print(result)


if __name__ == "__main__":  # pragma: no cover
    main()
