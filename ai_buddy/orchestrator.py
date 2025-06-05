import json
import logging
import os
import time
from dataclasses import dataclass
from typing import List


LOG_PATH = os.path.join("logs", "agent_executions.json")
MEM_PATH = os.path.join("tmp", "agent_mem.json")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class Task:
    id: int
    description: str


class BaseAgent:
    name: str

    def log_action(
        self, task_id: int, action: str, result: str, tokens: int = 0
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "task_id": task_id,
            "agent": self.name,
            "action": action,
            "tokens": tokens,
            "result": result,
        }
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")

        os.makedirs(os.path.dirname(MEM_PATH), exist_ok=True)
        with open(MEM_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")


class Planner(BaseAgent):
    name = "Planner"

    def plan(self, issue_body: str) -> List[Task]:
        steps = [
            line.strip("- ") for line in issue_body.strip().splitlines() if line.strip()
        ]
        tasks = [Task(i + 1, step) for i, step in enumerate(steps)]
        self.log_action(0, "plan", f"{len(tasks)} tasks generated")
        return tasks


class Coder(BaseAgent):
    name = "Coder"

    def apply_patch(self, task: Task) -> str:
        # Placeholder: implement patch application
        result = f"Patched: {task.description}"
        self.log_action(task.id, "patch", result)
        return result


class Tester(BaseAgent):
    name = "Tester"

    def run_checks(self) -> bool:
        import subprocess

        commands = [
            ["black", "--check", "."],
            ["ruff", "."],
            ["mypy", "--strict"],
            ["npm", "run", "lint"],
            ["npm", "run", "typecheck"],
            ["pytest"],
        ]
        success = True
        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.log_action(0, "run", f"{' '.join(cmd)} => {result.returncode}")
            if result.returncode != 0:
                success = False
        return success


class Reviewer(BaseAgent):
    name = "Reviewer"

    def review(self, success: bool) -> str:
        result = "Approved" if success else "Changes requested"
        self.log_action(0, "review", result)
        return result


class PRBot(BaseAgent):
    name = "PRBot"

    def update_pr(self, title: str, body: str, labels: List[str]) -> None:
        # Placeholder: would call GitHub API
        self.log_action(0, "pr", f"{title} | {labels}")


class Orchestrator:
    def __init__(self) -> None:
        self.planner = Planner()
        self.coder = Coder()
        self.tester = Tester()
        self.reviewer = Reviewer()
        self.prbot = PRBot()

    def run(self, issue_body: str) -> None:
        tasks = self.planner.plan(issue_body)
        max_attempts = 2
        attempt = 0
        success = False
        while attempt <= max_attempts and not success:
            for task in tasks:
                self.coder.apply_patch(task)
            success = self.tester.run_checks()
            if not success:
                attempt += 1
                if attempt > max_attempts:
                    break
                tasks = self.planner.plan(f"Retry after failure: {issue_body}")
        review_result = self.reviewer.review(success)
        label = [] if success else ["needs-human"]
        self.prbot.update_pr("Automated PR", review_result, label)


def main() -> None:
    issue_body = os.environ.get("ISSUE_BODY", "No issue body provided.")
    orch = Orchestrator()
    orch.run(issue_body)


if __name__ == "__main__":
    main()
