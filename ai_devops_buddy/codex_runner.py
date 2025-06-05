import json
import os
from datetime import datetime
from pathlib import Path

from .agents.issue_synthesizer import IssueSynthesizer
from .agents.planning_agent import PlanningAgent
from .agents.codex_worker_agent import CodexWorkerAgent
from .agents.validator_agent import ValidatorAgent
from .agents.pull_request_agent import PullRequestAgent


LOGS = Path("logs")
LOGS.mkdir(exist_ok=True)
AGENT_EXEC_LOG = LOGS / "agent_executions.json"
LLM_LOG = LOGS / "llm_events.ndjson"
COST_LOG = LOGS / "cost_metrics.json"


class MultiAgentRunner:
    def __init__(self):
        self.issue = IssueSynthesizer()
        self.planner = PlanningAgent()
        self.worker = CodexWorkerAgent()
        self.validator = ValidatorAgent()
        self.pr = PullRequestAgent()
        self.errors = 0

    def _log_agent(self, name, payload):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": name,
            "payload": payload,
        }
        with AGENT_EXEC_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def _log_cost(self, metrics):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            **metrics,
        }
        with COST_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def run(self, context):
        try:
            tasks = self.issue.run(context)
            self._log_agent("issue_synthesizer", tasks)

            plan = self.planner.run(tasks["tasks"])
            self._log_agent("planning_agent", plan)

            results = self.worker.run(plan)
            self._log_agent("codex_worker_agent", results)

            validated = self.validator.run(results)
            self._log_agent("validator_agent", validated)

            if os.getenv("LICENSE_KEY"):
                pr_result = self.pr.run(validated)
                self._log_agent("pull_request_agent", pr_result)
            else:
                pr_result = {"pr": "disabled"}
                self._log_agent("pull_request_agent", pr_result)

            self._log_cost({"tasks": len(plan)})

            return pr_result
        except Exception as e:
            self.errors += 1
            self._log_agent("error", {"message": str(e)})
            if self.errors > 3:
                self._log_agent("fallback", {"reason": "too many errors"})
            raise


def run(context: str):
    runner = MultiAgentRunner()
    return runner.run(context)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the AI DevOps Buddy pipeline")
    parser.add_argument("context", help="Issue or PR context")
    args = parser.parse_args()
    result = run(args.context)
    print(result)
