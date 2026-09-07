#!/usr/bin/env python3
"""
Generate OpenAI embeddings (text-embedding-3-small, 128 dims) for knowledge_base rows.
Run after applying migrations: python supabase/seed_embeddings.py
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 128


def main() -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not all([url, key, openai_key]):
        print("Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and OPENAI_API_KEY in .env")
        sys.exit(1)

    supabase = create_client(url, key)
    openai = OpenAI(api_key=openai_key)

    result = supabase.table("knowledge_base").select("id, title, content").execute()
    docs = result.data or []

    if not docs:
        print("No knowledge_base documents found. Run 002_sample_data.sql first.")
        sys.exit(1)

    for doc in docs:
        text = f"{doc['title']}\n{doc['content']}"
        response = openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        embedding = response.data[0].embedding

        supabase.table("knowledge_base").update({"embedding": embedding}).eq(
            "id", doc["id"]
        ).execute()
        print(f"Embedded: {doc['title']}")

    print(f"Done. Embedded {len(docs)} documents.")


if __name__ == "__main__":
    main()
