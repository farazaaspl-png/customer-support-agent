"""
CONCEPT 9: RAG + LangGraph
--------------------------
Retrieval-Augmented Generation: embed the user query, search Supabase pgvector,
and inject relevant knowledge-base chunks into the graph state for the LLM.
"""

from openai import OpenAI

from ai import db as pg
from ai.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, OPENAI_API_KEY

_openai = None


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=OPENAI_API_KEY)
    return _openai


def embed_text(text: str) -> list[float]:
    """Generate a 128-dimension embedding for the given text."""
    from ai.langfuse_tracing import is_langfuse_enabled

    if is_langfuse_enabled():
        from langfuse import observe

        @observe(name="embed_text", as_type="embedding")
        def _embed(input_text: str) -> list[float]:
            response = _get_openai().embeddings.create(
                model=EMBEDDING_MODEL,
                input=input_text,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            return response.data[0].embedding

        return _embed(text)

    response = _get_openai().embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


def semantic_search(query: str, top_k: int = 3, threshold: float = 0.25) -> list[dict]:
    """Search knowledge_base using pgvector cosine similarity via direct Postgres."""
    try:
        embedding = embed_text(query)
        return pg.semantic_search_db(embedding, top_k=top_k, threshold=threshold)
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
        if isinstance(similarity, float):
            similarity = f"{similarity:.2f}"
        parts.append(
            f"[{i}] {doc['title']} (category: {doc['category']}, relevance: {similarity})\n"
            f"{doc['content']}"
        )
    return "\n\n".join(parts)
