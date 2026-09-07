"""Session API routes — list, load, and manage conversation history."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai import conversation as conv

router = APIRouter()


class SessionOut(BaseModel):
    id: str
    thread_id: str
    title: str
    message_count: int
    summary: str | None = None
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


@router.get("/sessions")
async def list_sessions():
    """List all past conversations, newest first."""
    sessions = conv.list_sessions()
    return [
        {
            "id": str(s["id"]),
            "thread_id": s["thread_id"],
            "title": s["title"],
            "message_count": s["message_count"],
            "summary": s.get("summary"),
            "created_at": s["created_at"].isoformat(),
            "updated_at": s["updated_at"].isoformat(),
        }
        for s in sessions
    ]


@router.get("/sessions/{thread_id}/messages")
async def get_messages(thread_id: str):
    """Load full message history for a conversation."""
    session = conv.get_session_by_thread(thread_id)
    if not session:
        raise HTTPException(404, "Session not found")

    messages = conv.get_all_messages(session["id"])
    return {
        "thread_id": thread_id,
        "title": session["title"],
        "summary": session.get("summary"),
        "messages": [
            {
                "id": str(m["id"]),
                "role": m["role"],
                "content": m["content"],
                "created_at": m["created_at"].isoformat(),
            }
            for m in messages
        ],
    }
