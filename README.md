# AI DevOps Buddy

This repo contains a minimal full-stack web service with FastAPI and React.

## Development

### Backend

```bash
python -m pip install --quiet -r backend/requirements.txt
uvicorn backend.app:app --reload
```

### Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Run tests:

```bash
pytest -q backend
npm --prefix frontend test -- --watch=false
```
