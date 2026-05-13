"""Shared async Perplexity client for search-grounded enrichment.

Uses httpx to call Perplexity's chat completions API, which returns
web-searched, citation-backed responses. All consumers MUST check
is_available() before calling, and fall back to Claude-only paths
when Perplexity is not configured.

Design mirrors claude_client.py: singleton httpx client, rate-limit
semaphore, per-workflow token tracking.
"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Response model ─────────────────────────────────────────────────────────


@dataclass
class PerplexityResponse:
    """Parsed response from Perplexity API."""

    content: str
    citations: list[str]
    model: str
    usage: dict[str, int]
    latency_ms: int


# ── Rate-limit semaphore ──────────────────────────────────────────────────
# Perplexity has lower rate limits than Anthropic. Keep concurrency low.
PERPLEXITY_SEMAPHORE_LIMIT = 2
_perplexity_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _perplexity_semaphore
    if _perplexity_semaphore is None:
        _perplexity_semaphore = asyncio.Semaphore(PERPLEXITY_SEMAPHORE_LIMIT)
    return _perplexity_semaphore


# ── Per-workflow token tracking ───────────────────────────────────────────
_workflow_perplexity_usage: dict[int, int] = {}


def get_workflow_perplexity_usage(workflow_run_id: int) -> int:
    return _workflow_perplexity_usage.get(workflow_run_id, 0)


def clear_workflow_perplexity_usage(workflow_run_id: int) -> None:
    _workflow_perplexity_usage.pop(workflow_run_id, None)


# ── Singleton client ──────────────────────────────────────────────────────
_httpx_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=settings.perplexity_timeout)
    return _httpx_client


# ── Public API ────────────────────────────────────────────────────────────


def is_available() -> bool:
    """Check whether Perplexity API is configured and usable."""
    return bool(settings.perplexity_api_key)


async def search_and_analyze(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
    workflow_run_id: int | None = None,
) -> PerplexityResponse:
    """Call Perplexity chat completions API with web search.

    Args:
        system_prompt: Instructions for the search-grounded analysis.
        user_prompt: The query/data to search and analyze.
        model: Perplexity model (default: settings.perplexity_model).
        max_tokens: Max response tokens.
        temperature: Sampling temperature.
        workflow_run_id: For per-workflow token tracking (optional).

    Returns:
        PerplexityResponse with content, citations, usage, and latency.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses.
        RuntimeError: If Perplexity is not configured.
    """
    if not is_available():
        raise RuntimeError(
            "Perplexity API is not configured. Set PERPLEXITY_API_KEY in .env."
        )

    resolved_model = model or settings.perplexity_model
    client = _get_client()

    payload = {
        "model": resolved_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    sem = _get_semaphore()
    if sem.locked():
        logger.info("Perplexity semaphore full, waiting for a slot...")

    start = time.monotonic()
    async with sem:
        logger.info(
            "Perplexity API call starting (model=%s, semaphore acquired)",
            resolved_model,
        )
        response = await client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.perplexity_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()

    latency_ms = int((time.monotonic() - start) * 1000)
    data = response.json()

    # Extract content
    choices = data.get("choices", [])
    content = choices[0]["message"]["content"] if choices else ""

    # Extract citations (Perplexity returns these at the top level)
    citations = data.get("citations", [])

    # Extract usage
    usage_data = data.get("usage", {})
    usage = {
        "prompt_tokens": usage_data.get("prompt_tokens", 0),
        "completion_tokens": usage_data.get("completion_tokens", 0),
    }

    total_tokens = usage["prompt_tokens"] + usage["completion_tokens"]

    # Track per-workflow usage
    if workflow_run_id is not None:
        _workflow_perplexity_usage[workflow_run_id] = (
            _workflow_perplexity_usage.get(workflow_run_id, 0) + total_tokens
        )

    logger.info(
        "Perplexity API complete: model=%s, latency=%dms, citations=%d, tokens=%d",
        resolved_model,
        latency_ms,
        len(citations),
        total_tokens,
    )

    return PerplexityResponse(
        content=content,
        citations=citations,
        model=data.get("model", resolved_model),
        usage=usage,
        latency_ms=latency_ms,
    )
