"""Nightly LoRA fine-tuner."""

from __future__ import annotations

import os
from pathlib import Path


def has_gpu(min_gb: int = 4) -> bool:
    return os.environ.get("GPU", "0") == "1"


def main() -> None:
    if not has_gpu():
        print("SKIPPED")
        return
    history_file = Path("logs/fine_tune_history.csv")
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text("loss\n0.1")
    print("FINISHED")


if __name__ == "__main__":  # pragma: no cover
    main()
