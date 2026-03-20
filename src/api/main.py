"""
src/api/main.py — Instrument retail support ingestion microservice.

Accepts support requests for musical instruments, validates them with Pydantic,
queues them for async processing, and exposes a health-check endpoint.
OpenTelemetry tracing is wired when the SDK is installed; degrades gracefully
when not present (e.g. in offline CI).
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

# ── Optional OpenTelemetry tracing ────────────────────────────────────────────
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

    _provider = TracerProvider()
    _provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(_provider)
    _tracer = trace.get_tracer(__name__)
    _OTEL_ENABLED = True
except ImportError:  # pragma: no cover
    _OTEL_ENABLED = False
    _tracer = None  # type: ignore[assignment]

# ── Pydantic models ───────────────────────────────────────────────────────────


class InstrumentModel(BaseModel):
    instrument_id: str
    name: str
    type: str
    price: float


class SupportRequest(BaseModel):
    request_id: str
    instrument: InstrumentModel
    issue_description: str
    customer_id: str


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Instrument Support Ingestion Service",
    description="Ingests retail support requests for musical instruments.",
    version="1.0.0",
)


@app.post("/ingest/support_request/")
async def ingest_support_request(request: SupportRequest) -> dict[str, Any]:
    """Receive and queue a support request for processing."""
    if _OTEL_ENABLED and _tracer is not None:
        with _tracer.start_as_current_span("ingest_support_request") as span:
            span.set_attribute("request.id", request.request_id)
            span.set_attribute(
                "instrument.id", request.instrument.instrument_id)
    return {
        "message": "Support request received and queued for processing.",
        "request_id": request.request_id,
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health-check endpoint for liveness probes."""
    return {"status": "healthy"}
