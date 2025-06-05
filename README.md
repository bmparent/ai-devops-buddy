# AI DevOps Buddy

```
+-------------+     +--------------+      +----------------+
|  Frontend   | <-> | FastAPI SSE  | <->  |  Orchestrator  |
+-------------+     +--------------+      +----------------+
```

## Dev Quick Start

```bash
pip install -e .
cd frontend && npm install && npm run lint && npm test
```

![Console](assets/console.gif)

## Why This Wows Senior Engineers

- **Glass-Box Reasoning** via `AgentConsole.tsx` shows step-by-step actions.
- **Self-Tuning** with nightly LoRA fine-tunes local models.
- **Real-Time Feedback** surfaces metrics and auto rollback PRs.
- **Cost Awareness** routes tasks based on token spend.
- **Plugin Marketplace** adds skills by dropping files in `plugins/`.
- **Deterministic Replay** verifies identical diffs for tasks.
