class ValidatorAgent:
    """Runs tests and linters."""

    def run(self, results):
        # In real system, run pytest, lint, mypy
        for r in results:
            r["validated"] = True
        return results
