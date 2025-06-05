"""FastAPI server exposing SSE for agent stream."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


async def event_generator(task_id: str) -> AsyncGenerator[str, None]:
    for i in range(3):
        await asyncio.sleep(0.1)
        yield json.dumps(
            {
                "role": "agent",
                "action": f"step {i}",
                "confidence": 0.9,
                "tokens": 5,
                "elapsed_ms": i * 100,
            }
        )


@app.get("/stream/agent/{task_id}")  # type: ignore[misc]
async def stream_agent(task_id: str) -> StreamingResponse:
    async def gen() -> AsyncGenerator[bytes, None]:
        async for event in event_generator(task_id):
            yield f"data: {event}\n\n".encode()

    return StreamingResponse(gen(), media_type="text/event-stream")
