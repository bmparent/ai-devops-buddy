"""Track token spend and route models."""

from __future__ import annotations

import json
import os
from pathlib import Path

MONTHLY_TOKEN_BUDGET = int(os.environ.get("MONTHLY_TOKEN_BUDGET", "100000"))
COST_FILE = Path("logs/cost_metrics.json")


class BudgetManager:
    """Track usage and choose models."""

    def __init__(self) -> None:
        self.tokens: int = 0
        if COST_FILE.exists():
            try:
                data = json.loads(COST_FILE.read_text())
                self.tokens = int(data.get("tokens", 0))
            except Exception:
                self.tokens = 0

    @property
    def usage_ratio(self) -> float:
        return self.tokens / MONTHLY_TOKEN_BUDGET

    def record_tokens(self, model: str, amount: int) -> None:
        self.tokens += amount
        COST_FILE.parent.mkdir(parents=True, exist_ok=True)
        COST_FILE.write_text(json.dumps({"tokens": self.tokens}))

    def choose_model(self, complexity: int) -> str:
        if self.usage_ratio >= 0.8 and complexity <= 1:
            return "local-7b"
        return "gpt-4o"


__all__ = ["BudgetManager"]
