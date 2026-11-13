"""
Main FastAPI Gateway entrypoint for The Relay.
Serves on port 8000 by default.
"""

from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(
    title="The Relay — ML Engineering API Gateway",
    description="Observable, resilient, citation-grounded RAG orchestrator for research papers.",
    version="1.0.0"
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    from config.settings import settings
    uvicorn.run("src.api.main:app", host=settings.api_host, port=settings.api_port, reload=True)

