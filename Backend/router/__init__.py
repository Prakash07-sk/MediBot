from fastapi import APIRouter
from fastapi.responses import JSONResponse
from .conversation_router import router as conversation_router
from utils import config

router = APIRouter(prefix=config.BACKEND_API_ENDPOINT)

@router.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(content={"status": "ok"})

router.include_router(conversation_router, prefix="/chat", tags=["Conversation"])

__all__ = ["router"]
