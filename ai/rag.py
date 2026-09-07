"""
CONCEPT 9: RAG + LangGraph
--------------------------
Retrieval-Augmented Generation: embed the user query, search Supabase pgvector,
and inject relevant knowledge-base chunks into the graph state for the LLM.
"""

from typing import Optional

from openai import OpenAI

from ai.config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)

_supabase = None
_openai = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client

        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=OPENAI_API_KEY)
    return _openai


def embed_text(text: str) -> list[float]:
    """Generate a 128-dimension embedding for the given text."""
    response = _get_openai().embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


def semantic_search(query: str, top_k: int = 3, threshold: float = 0.3) -> list[dict]:
    """
    Search knowledge_base using pgvector cosine similarity.
    Falls back to keyword search if embeddings are not seeded yet.
    """
    try:
        embedding = embed_text(query)
        sb = _get_supabase()
        result = sb.rpc(
            "match_knowledge_base",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": top_k,
            },
        ).execute()
        if result.data:
            return result.data
    except Exception:
        pass

    # Fallback: simple text search when embeddings are missing
    try:
        sb = _get_supabase()
        result = (
            sb.table("knowledge_base")
            .select("id, title, content, category")
            .ilike("content", f"%{query[:50]}%")
            .limit(top_k)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def build_rag_context(query: str) -> str:
    """Retrieve and format knowledge-base chunks for injection into the LLM prompt."""
    results = semantic_search(query, top_k=3)
    if not results:
        return "No relevant policy documents found."

    parts = []
    for i, doc in enumerate(results, 1):
        similarity = doc.get("similarity", "N/A")
        parts.append(
            f"[{i}] {doc['title']} (category: {doc['category']}, relevance: {similarity})\n"
            f"{doc['content']}"
        )
    return "\n\n".join(parts)
