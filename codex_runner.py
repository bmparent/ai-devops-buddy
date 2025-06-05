#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def run(cmd: str) -> None:
    print(f"+ {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: codex_runner.py <task-file>")
        raise SystemExit(1)
    task_path = Path(sys.argv[1])
    task = json.loads(task_path.read_text())
    patch = task.get("diff")
    if patch:
        subprocess.run(["git", "apply"], input=patch.encode(), check=True)
    run("python -m pip install --quiet -r backend/requirements.txt")
    run("npm --prefix frontend ci")
    run("pytest -q backend")
    run("npm --prefix frontend test -- --watch=false")
    run("git status --short")
    print("Ready to push branch/PR.")


if __name__ == "__main__":
    main()
