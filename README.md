# ai-devops-buddy

[![CI](https://github.com/your-org/ai-devops-buddy/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/ai-devops-buddy/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/your-org/ai-devops-buddy/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/ai-devops-buddy)

This project showcases a simple full-stack pipeline with a FastAPI backend and a React frontend. It also includes a self-maintainer script that uses Codex to open pull requests.

```
+------------+       +-------------+
|  frontend  | <---> |   backend   |
+------------+       +-------------+
```

## Local Development

```bash
make dev
```

Start the services:

```bash
docker compose up --build
```

Open <http://localhost:3000> to view the app.
