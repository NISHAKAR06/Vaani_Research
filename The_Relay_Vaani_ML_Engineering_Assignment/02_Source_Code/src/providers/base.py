"""
Base ModelProvider interface and standardized response schemas for The Relay.
Used identically by GroqProvider and SimulatorProvider.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from pydantic import BaseModel, Field

class UsageMetadata(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ProviderResponse(BaseModel):
    content: str
    model: str
    source: str  # "real" or "stand-in"
    status_code: int = 200
    usage: UsageMetadata = Field(default_factory=UsageMetadata)
    first_token_latency_ms: Optional[float] = None
    total_latency_ms: float = 0.0
    headers: Dict[str, str] = Field(default_factory=dict)
    retry_after: Optional[float] = None
    raw_error: Optional[str] = None

class StreamChunk(BaseModel):
    text: str
    is_first: bool = False
    is_final: bool = False
    usage: Optional[UsageMetadata] = None
    latency_from_start_ms: float = 0.0

class ModelProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 25.0
    ) -> ProviderResponse:
        """Execute chat completion request, returning a structured ProviderResponse."""
        raise NotImplementedError

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 25.0
    ) -> AsyncIterator[StreamChunk]:
        """Execute chat completion request yielding incremental StreamChunk items."""
        raise NotImplementedError

