from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from Schema.conversation_schema import ConversationHistoryPayload  
from controller import conversation_controller

router = APIRouter()

@router.post("/")
async def chat(payload: ConversationHistoryPayload):
    # Implement your logic here
    return await conversation_controller.chat_data(payload)
