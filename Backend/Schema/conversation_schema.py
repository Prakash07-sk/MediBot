from pydantic import BaseModel
from typing import List

class ConversationEntry(BaseModel):
    role: str
    content: str

class ConversationHistoryPayload(BaseModel):
    conversation_history: List[ConversationEntry] = []
    query: str