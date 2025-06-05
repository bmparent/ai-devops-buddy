"""Simple orchestrator with limited functionality."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Dict

from .budget_manager import BudgetManager

ALLOWED_TOOLS_PATH = Path("allowed_tools.yaml")


class Orchestrator:
    """Orchestrator managing agent tasks."""

    def __init__(self) -> None:
        self.budget = BudgetManager()
        self.skills: Dict[str, Any] = {}
        self._load_plugins()

    def _load_plugins(self) -> None:
        plugins_dir = Path("plugins")
        if not plugins_dir.exists():
            return
        for child in plugins_dir.iterdir():
            plugin_file = child / "plugin.py"
            if plugin_file.exists():
                module_name = f"plugins.{child.name}.plugin"
                module = importlib.import_module(module_name)
                if hasattr(module, "register"):
                    skill = module.register()
                    self.skills[child.name] = skill

    def run_task(self, task: str, complexity: int = 1) -> str:
        model = self.budget.choose_model(complexity)
        # Fake execution
        result = f"{model}:{task}"
        self.budget.record_tokens(model, 10)
        return result


__all__ = ["Orchestrator"]
