"""FastAPI application for the Customer Support AI Agent."""

import os
import sys
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root so `ai` package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.routes import chat, hitl, sessions

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Customer Support AI Agent",
    description="LangGraph-powered customer support chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(hitl.router, prefix="/api/hitl", tags=["hitl"])


@app.get("/health")
async def health():
    return {"status": "ok"}
