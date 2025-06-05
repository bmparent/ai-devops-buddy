# AI DevOps Buddy

This repository demonstrates a minimal multi-agent DevOps assistant. It is a simplified example showing how the platform can be refactored into modular agents.

## Architecture

```
Issue -> IssueSynthesizer -> PlanningAgent -> CodexWorker -> Validator -> PullRequestAgent
```

## Setup

```bash
pip install -r requirements.txt
```

A `LICENSE_KEY` environment variable enables the Pull Request Agent.
