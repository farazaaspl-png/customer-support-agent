"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Langfuse (LLM tracing & token usage)
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "true").lower() in ("1", "true", "yes")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 128
CHAT_MODEL = "gpt-4o-mini"

MAX_RETRIES = 3

# Postgres schema for all app tables
DB_SCHEMA = os.getenv("DB_SCHEMA", "customer_support_agent")

# Conversation context management
MAX_CONTEXT_MESSAGES = 10   # messages sent to LLM per turn
SUMMARIZE_THRESHOLD = 20    # auto-summarize older messages when count exceeds this
