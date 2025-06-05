class CodexWorkerAgent:
    """Writes code and tests for each task."""

    def run(self, tasks):
        results = []
        for task in tasks:
            # In real agent, call Codex to implement code
            results.append({"task": task, "status": "done"})
        return results
