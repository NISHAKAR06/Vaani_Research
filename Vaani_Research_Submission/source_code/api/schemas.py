"""
FastAPI Pydantic Schemas for The Relay HTTP Service (Port 8000).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., description="Technical user query regarding the 3-paper library.")
    retrieval_setting: str = Field(default="A", description="Retrieval configuration: 'A', 'B', or 'C'.")
    stream: bool = Field(default=False, description="Enable Server-Sent Events (SSE) streaming.")
    source: str = Field(default="stand-in", description="Provider source: 'real' or 'stand-in'.")
    timeout_seconds: float = Field(default=25.0, description="End-to-end request timeout deadline.")

class CitationSchema(BaseModel):
    paper: str
    page: int
    section: Optional[str] = ""
    raw: str

class QueryResponse(BaseModel):
    request_id: str
    query: str
    answer: str
    status: str
    answer_grade: str
    retrieval_setting: str
    source: str
    tokens_in: int
    tokens_out: int
    retries: int
    first_token_ms: Optional[float]
    total_ms: float
    citations: List[CitationSchema]
    latency_breakdown: Dict[str, float]

