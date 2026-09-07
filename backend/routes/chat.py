"""Chat API routes."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.agent_service import get_thread_state, run_chat

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    thread_id: Optional[str] = Field(None, description="Conversation thread ID for memory")


class ChatResponse(BaseModel):
    thread_id: str
    response: str
    agent_status: str
    intent: Optional[str] = None
    pending_refund: Optional[dict] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the customer support agent."""
    result = run_chat(request.message, request.thread_id)
    return ChatResponse(**{k: result[k] for k in ChatResponse.model_fields})


@router.get("/chat/{thread_id}")
async def get_chat_state(thread_id: str):
    """Get the current state of a conversation thread."""
    return get_thread_state(thread_id)
