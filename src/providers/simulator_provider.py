"""
SimulatorProvider implementation of ModelProvider.
Calls the Stand-in Model Service HTTP API (http://127.0.0.1:8001/v1/chat/completions)
with support for streaming, latency measurement, and rate-limit header parsing.
"""

import time
import json
from typing import List, Dict, Any, Optional, AsyncIterator
import httpx

from config.settings import settings
from src.providers.base import ModelProvider, ProviderResponse, StreamChunk, UsageMetadata

class SimulatorProvider(ModelProvider):
    def __init__(self, base_url: Optional[str] = None, model: str = "llama-3.3-70b-versatile-standin", timeout: float = 25.0):
        self.base_url = (base_url or settings.standin_url).rstrip("/")
        self.model = model
        self.timeout = timeout
        self.source = "stand-in"

    def _extract_headers(self, raw_headers: httpx.Headers) -> Dict[str, str]:
        extracted = {}
        for k, v in raw_headers.items():
            k_lower = k.lower()
            if k_lower.startswith("x-ratelimit-") or k_lower == "retry-after":
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
        req_timeout = timeout or self.timeout
        start_time = time.perf_counter()
        url = f"{self.base_url}/v1/chat/completions"

        if stream:
            # Handle streaming
            chunks_content = []
            first_token_time = None
            async for chunk in self.generate_stream(messages, temperature, max_tokens, req_timeout):
                if chunk.is_first and first_token_time is None:
                    first_token_time = chunk.latency_from_start_ms
                if chunk.text:
                    chunks_content.append(chunk.text)
            
            total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ProviderResponse(
                content="".join(chunks_content),
                model=self.model,
                source="stand-in",
                status_code=200,
                first_token_latency_ms=first_token_time,
                total_latency_ms=round(total_elapsed_ms, 2)
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=req_timeout) as client:
            try:
                resp = await client.post(url, json=payload)
                total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                headers = self._extract_headers(resp.headers)

                if resp.status_code == 429:
                    retry_after = None
                    if "retry-after" in headers:
                        try:
                            retry_after = float(headers["retry-after"])
                        except ValueError:
                            pass
                    return ProviderResponse(
                        content="",
                        model=self.model,
                        source="stand-in",
                        status_code=429,
                        total_latency_ms=round(total_elapsed_ms, 2),
                        headers=headers,
                        retry_after=retry_after,
                        raw_error=resp.text
                    )

                if resp.status_code != 200:
                    return ProviderResponse(
                        content="",
                        model=self.model,
                        source="stand-in",
                        status_code=resp.status_code,
                        total_latency_ms=round(total_elapsed_ms, 2),
                        headers=headers,
                        raw_error=resp.text
                    )

                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage_raw = data.get("usage", {})
                usage = UsageMetadata(
                    prompt_tokens=usage_raw.get("prompt_tokens", 0),
                    completion_tokens=usage_raw.get("completion_tokens", 0),
                    total_tokens=usage_raw.get("total_tokens", 0)
                )

                # For stand-in, approximate first token as ~45% of total
                first_token_ms = round(total_elapsed_ms * 0.45, 2)

                return ProviderResponse(
                    content=content,
                    model=self.model,
                    source="stand-in",
                    status_code=200,
                    usage=usage,
                    first_token_latency_ms=first_token_ms,
                    total_latency_ms=round(total_elapsed_ms, 2),
                    headers=headers
                )

            except httpx.TimeoutException:
                total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return ProviderResponse(
                    content="",
                    model=self.model,
                    source="stand-in",
                    status_code=408,
                    total_latency_ms=round(total_elapsed_ms, 2),
                    raw_error="Simulator request timeout"
                )
            except Exception as e:
                total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return ProviderResponse(
                    content="",
                    model=self.model,
                    source="stand-in",
                    status_code=500,
                    total_latency_ms=round(total_elapsed_ms, 2),
                    raw_error=str(e)
                )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: Optional[float] = None
    ) -> AsyncIterator[StreamChunk]:
        req_timeout = timeout or self.timeout
        start_time = time.perf_counter()
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=req_timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                is_first = True
                async for line in resp.aiter_lines():
                    now_ms = (time.perf_counter() - start_time) * 1000.0
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        delta = chunk_json["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield StreamChunk(
                                text=delta,
                                is_first=is_first,
                                is_final=False,
                                latency_from_start_ms=round(now_ms, 2)
                            )
                            is_first = False
                    except Exception:
                        continue

                final_ms = (time.perf_counter() - start_time) * 1000.0
                yield StreamChunk(
                    text="",
                    is_first=False,
                    is_final=True,
                    latency_from_start_ms=round(final_ms, 2)
                )

