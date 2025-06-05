.PHONY: dev

dev:
python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install
