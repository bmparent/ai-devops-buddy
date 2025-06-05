# ai-devops-buddy

```
+---------+       +---------+       +---------+
| Planner |-----> | Coder   |-----> | Tester  |
+---------+       +---------+       +---------+
                                        |
                                        v
                                   +---------+
                                   |Reviewer |
                                   +---------+
                                        |
                                        v
                                   +---------+
                                   |  PRBot  |
                                   +---------+
```

Agents communicate via `tmp/agent_mem.json` and log actions to `logs/agent_executions.json`. Docker compose spins up backend, frontend and worker containers.

## Quick Start

```bash
make dev
```

This builds containers and streams logs.

## Submitting Issues

Open a GitHub Issue describing tasks as bullet points. The worker polls issues and processes them automatically.
