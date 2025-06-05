# AGENTS Handbook

## Commit and PR Guidelines
- Use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`).
- Keep messages concise.
- PR descriptions must include test results.

## Coding Style
- Format Python with `black` and `isort`.
- Type-check with `mypy --strict`.
- Lint frontend with `eslint` and format with `prettier`.

## Workflow
- Before committing, run:
  - `pytest -q backend`
  - `npm --prefix frontend test -- --watch=false`

## Extending the Agent
- `codex_runner.py` applies diffs, runs tests, and prepares PRs.
- Pin all dependency versions.
