"""
Groq API ModelProvider implementation for The Relay.
Directly captures rate-limit response headers, usage metadata, and streaming TTFT.
Configured with max_retries=0 to disable opaque automatic retries for measurable latency.
"""

import time
import json
from typing import List, Dict, Any, Optional, AsyncIterator
import httpx
from groq import AsyncGroq, APIError, RateLimitError, APITimeoutError

from config.settings import settings
from src.providers.base import ModelProvider, ProviderResponse, StreamChunk, UsageMetadata

class GroqProvider(ModelProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 25.0
    ):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.timeout = timeout
        
        # AsyncGroq client with max_retries=0 to prevent hidden SDK retries
        if self.api_key:
            self.client = AsyncGroq(
                api_key=self.api_key,
                max_retries=0,
                timeout=self.timeout
            )
        else:
            self.client = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.client is not None)

    def _extract_headers(self, raw_headers: Any) -> Dict[str, str]:
        """Extract x-ratelimit and retry-after headers from response."""
        extracted = {}
        target_prefixes = ("x-ratelimit-", "retry-after")
        for k, v in raw_headers.items():
            k_lower = k.lower()
            if any(k_lower.startswith(p) for p in target_prefixes):
                extracted[k_lower] = str(v)
        return extracted

    async def generate(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: Optional[float] = None
    ) -> ProviderResponse:
        if not self.is_configured():
            raise RuntimeError(
                "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your .env file."
            )

        req_timeout = timeout or self.timeout
        start_time = time.perf_counter()

        if stream:
            # Aggregate streaming chunks to record first-token time
            chunks_content = []
            first_token_time = None
            usage = UsageMetadata()
            headers = {}

            stream_iter = self.generate_stream(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=req_timeout
            )

            async for chunk in stream_iter:
                if chunk.is_first and first_token_time is None:
                    first_token_time = chunk.latency_from_start_ms
                if chunk.text:
                    chunks_content.append(chunk.text)
                if chunk.usage:
                    usage = chunk.usage

            total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ProviderResponse(
                content="".join(chunks_content),
                model=self.model,
                source="real",
                status_code=200,
                usage=usage,
                first_token_latency_ms=first_token_time,
                total_latency_ms=round(total_elapsed_ms, 2),
                headers=headers
            )

        # Standard non-streaming request
        try:
            # We use raw response to capture HTTP headers reliably
            raw_resp = await self.client.chat.completions.with_raw_response.create(
                messages=messages,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=req_timeout
            )
            total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            
            headers = self._extract_headers(raw_resp.headers)
            completion = raw_resp.parse()
            
            content = completion.choices[0].message.content or ""
            usage = UsageMetadata(
                prompt_tokens=completion.usage.prompt_tokens if completion.usage else 0,
                completion_tokens=completion.usage.completion_tokens if completion.usage else 0,
                total_tokens=completion.usage.total_tokens if completion.usage else 0
            )

            return ProviderResponse(
                content=content,
                model=self.model,
                source="real",
                status_code=200,
                usage=usage,
                first_token_latency_ms=round(total_elapsed_ms, 2),  # non-streaming: first token = complete
                total_latency_ms=round(total_elapsed_ms, 2),
                headers=headers
            )

        except RateLimitError as e:
            total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            headers = self._extract_headers(getattr(e.response, "headers", {}))
            retry_after = None
            if "retry-after" in headers:
                try:
                    retry_after = float(headers["retry-after"])
                except ValueError:
                    pass
            return ProviderResponse(
                content="",
                model=self.model,
                source="real",
                status_code=429,
                total_latency_ms=round(total_elapsed_ms, 2),
                headers=headers,
                retry_after=retry_after,
                raw_error=str(e)
            )

        except APITimeoutError as e:
            total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ProviderResponse(
                content="",
                model=self.model,
                source="real",
                status_code=408,
                total_latency_ms=round(total_elapsed_ms, 2),
                raw_error=f"Timeout: {e}"
            )

        except APIError as e:
            total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            status_code = getattr(e, "status_code", 500) or 500
            headers = self._extract_headers(getattr(e.response, "headers", {}))
            return ProviderResponse(
                content="",
                model=self.model,
                source="real",
                status_code=status_code,
                total_latency_ms=round(total_elapsed_ms, 2),
                headers=headers,
                raw_error=str(e)
            )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: Optional[float] = None
    ) -> AsyncIterator[StreamChunk]:
        if not self.is_configured():
            raise RuntimeError("GROQ_API_KEY is not configured.")

        req_timeout = timeout or self.timeout
        start_time = time.perf_counter()
        is_first = True

        stream = await self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            timeout=req_timeout
        )

        async for chunk in stream:
            now_ms = (time.perf_counter() - start_time) * 1000.0
            delta_content = chunk.choices[0].delta.content or ""
            
            yield StreamChunk(
                text=delta_content,
                is_first=is_first,
                is_final=False,
                latency_from_start_ms=round(now_ms, 2)
            )
            if is_first and delta_content:
                is_first = False

        final_ms = (time.perf_counter() - start_time) * 1000.0
        yield StreamChunk(
            text="",
            is_first=False,
            is_final=True,
            latency_from_start_ms=round(final_ms, 2)
        )

