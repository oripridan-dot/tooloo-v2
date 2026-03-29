from __future__ import annotations
import httpx
import json
import uuid
import logging
from typing import AsyncGenerator, Optional, List
from .models import TooLooRequest, TooLooResponse

logger = logging.getLogger("TooLooSDK")

class TooLooClient:
    """The high-level interface for interacting with the TooLoo V2 engine."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 60.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http_client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Closes the underlying HTTP client."""
        await self._http_client.aclose()

    async def execute(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        intent: str = "IDEATE",
        domain: str = "backend"
    ) -> TooLooResponse:
        """Executes a single mandate through the TooLoo engine."""
        request_obj = TooLooRequest(
            prompt=prompt,
            session_id=session_id or f"sdk-{uuid.uuid4().hex[:6]}",
            intent=intent,
            domain=domain
        )
        
        response = await self._http_client.post(
            "/v2/execute",
            json=request_obj.model_dump()
        )
        response.raise_for_status()
        return TooLooResponse.model_validate(response.json())

    async def stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        intent: str = "IDEATE",
        domain: str = "backend"
    ) -> AsyncGenerator[str, None]:
        """Streams response tokens from the TooLoo engine via Server-Sent Events."""
        request_data = {
            "prompt": prompt,
            "session_id": session_id or f"sdk-stream-{uuid.uuid4().hex[:6]}",
            "intent": intent,
            "domain": domain
        }

        async with self._http_client.stream(
            "POST",
            "/v2/stream",
            json=request_data
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line[6:].strip()
                elif line.strip() == "":
                    continue
                else:
                    # Potential non-data lines (e.g. comments, heartbeat)
                    continue

# Support for synchronous-style context manager if needed in the future
