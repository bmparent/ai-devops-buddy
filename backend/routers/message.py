from fastapi import APIRouter

router = APIRouter()


@router.get("/message")
async def read_message():
    return {"message": "Hello from FastAPI"}
