#!/usr/bin/env python3
"""
Generate OpenAI embeddings (text-embedding-3-small, 128 dims) for knowledge_base rows.
Run after applying migrations: python supabase/seed_embeddings.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from openai import OpenAI

from ai.db import get_conn

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 128


def main() -> None:
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("Set OPENAI_API_KEY and DATABASE_URL in .env")
        sys.exit(1)

    openai = OpenAI(api_key=openai_key)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, content FROM knowledge_base")
            docs = cur.fetchall()

    if not docs:
        print("No knowledge_base documents found. Run migrations first.")
        sys.exit(1)

    for doc in docs:
        text = f"{doc['title']}\n{doc['content']}"
        response = openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        embedding = response.data[0].embedding

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE knowledge_base SET embedding = %s::vector WHERE id = %s",
                    (str(embedding), doc["id"]),
                )
        print(f"Embedded: {doc['title']}")

    print(f"Done. Embedded {len(docs)} documents.")


if __name__ == "__main__":
    main()
