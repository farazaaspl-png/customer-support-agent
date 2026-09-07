"""
Conversation history — persist sessions/messages and manage LLM context efficiently.

Concept: store ALL messages in DB for the UI, but only send the last N messages
(+ optional summary of older ones) to the LangGraph agent.
"""

import uuid
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ai.config import CHAT_MODEL, MAX_CONTEXT_MESSAGES, OPENAI_API_KEY, SUMMARIZE_THRESHOLD
from ai.db import get_conn

# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


def get_or_create_session(thread_id: Optional[str] = None, first_message: str = "") -> dict[str, Any]:
    """Get existing session by thread_id or create a new one."""
    thread_id = thread_id or str(uuid.uuid4())
    title = _title_from_message(first_message) if first_message else "New conversation"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM chat_sessions WHERE thread_id = %s", (thread_id,))
            row = cur.fetchone()
            if row:
                return dict(row)

            cur.execute(
                """
                INSERT INTO chat_sessions (thread_id, title)
                VALUES (%s, %s)
                RETURNING *
                """,
                (thread_id, title),
            )
            return dict(cur.fetchone())


def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, thread_id, title, message_count, summary, created_at, updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_session_by_thread(thread_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM chat_sessions WHERE thread_id = %s", (thread_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def touch_session(session_id: str, title: Optional[str] = None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            if title:
                cur.execute(
                    "UPDATE chat_sessions SET updated_at = NOW(), title = %s WHERE id = %s",
                    (title, session_id),
                )
            else:
                cur.execute(
                    "UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s",
                    (session_id,),
                )


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def save_message(session_id: str, role: str, content: str) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (%s, %s, %s)
                RETURNING id, role, content, created_at
                """,
                (session_id, role, content),
            )
            msg = dict(cur.fetchone())
            cur.execute(
                """
                UPDATE chat_sessions
                SET message_count = message_count + 1, updated_at = NOW()
                WHERE id = %s
                """,
                (session_id,),
            )
            return msg


def get_all_messages(session_id: str) -> list[dict[str, Any]]:
    """Full history for UI display."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, role, content, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                """,
                (session_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_recent_messages(session_id: str, limit: int = MAX_CONTEXT_MESSAGES) -> list[dict[str, Any]]:
    """Last N messages for LLM context window."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content FROM (
                    SELECT role, content, created_at
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                ) sub ORDER BY sub.created_at ASC
                """,
                (session_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Context building (efficiency for long conversations)
# ---------------------------------------------------------------------------


def build_langchain_messages(session: dict[str, Any]) -> list:
    """
    Build message list for LangGraph from DB.
    Uses summary + recent messages only — not the full history.
    """
    messages: list = []

    if session.get("summary"):
        messages.append(
            SystemMessage(
                content=f"Summary of earlier messages in this conversation:\n{session['summary']}"
            )
        )

    for m in get_recent_messages(session["id"], MAX_CONTEXT_MESSAGES):
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        else:
            messages.append(AIMessage(content=m["content"]))

    return messages


def maybe_summarize(session_id: str) -> None:
    """
    When message count exceeds threshold, summarize older messages into session.summary.
    Keeps LLM context small while preserving conversation meaning.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT message_count, summary FROM chat_sessions WHERE id = %s",
                (session_id,),
            )
            session = cur.fetchone()
            if not session or session["message_count"] < SUMMARIZE_THRESHOLD:
                return

            # Fetch messages that fall outside the context window
            cur.execute(
                """
                SELECT role, content FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                OFFSET 0
                LIMIT %s
                """,
                (session_id, session["message_count"] - MAX_CONTEXT_MESSAGES),
            )
            old_msgs = cur.fetchall()
            if not old_msgs:
                return

            text = "\n".join(f"{m['role']}: {m['content']}" for m in old_msgs)
            summary = _summarize_text(text, session.get("summary"))

            cur.execute(
                "UPDATE chat_sessions SET summary = %s WHERE id = %s",
                (summary, session_id),
            )


def _summarize_text(text: str, existing_summary: Optional[str] = None) -> str:
    """Use LLM to compress older messages into a short summary."""
    from langchain_openai import ChatOpenAI

    prefix = f"Existing summary: {existing_summary}\n\n" if existing_summary else ""
    prompt = (
        f"{prefix}Summarize these older chat messages in 2-3 sentences. "
        f"Keep key facts (order numbers, customer emails, decisions):\n\n{text}"
    )
    llm = ChatOpenAI(model=CHAT_MODEL, api_key=OPENAI_API_KEY, temperature=0)
    return llm.invoke([HumanMessage(content=prompt)]).content


def _title_from_message(message: str, max_len: int = 50) -> str:
    title = message.strip().replace("\n", " ")
    return (title[:max_len] + "…") if len(title) > max_len else title or "New conversation"
