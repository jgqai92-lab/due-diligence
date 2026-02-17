"""Shared async Claude client for all workflow services (IST, HFRT).

Uses AsyncAnthropic with structured output parsing via Pydantic models.
Each workflow step calls this with a step-specific system prompt and user prompt.

Invariants enforced:
- INV-AI-01: Content/instruction separation (system = instructions, user = data)
- INV-AI-03: Pydantic-validated Claude outputs
- INV-AI-06: No API keys in logs/errors/SSE
- INV-PE-02: Claude API calls have timeouts
- D-01/ATLAS-5: Per-workflow token budget tracking (500K limit)
"""

import asyncio
import contextvars
import json
import logging
from typing import TypeVar, Type

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ── Model tier mapping ──────────────────────────────────────────────────────
# Maps short tier names (stored in workflow_steps.model_tier) to full model IDs.
# Step handlers pass model="opus" or model="sonnet"; this resolves to the real ID.
# Unrecognized values fall through to settings.claude_model as a safety default.
MODEL_IDS: dict[str, str] = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-5-20250929",
}


def resolve_model_id(model: str | None) -> str:
    """Resolve a model tier name or full model ID to a concrete model ID.

    Priority:
    1. If model is a known tier name ("opus", "sonnet"), return the mapped ID.
    2. If model looks like a full model ID (contains "-"), return as-is.
    3. Fall back to settings.claude_model.
    """
    if model and model in MODEL_IDS:
        return MODEL_IDS[model]
    if model and "-" in model:
        # Already a full model ID (e.g. "claude-sonnet-4-20250514")
        return model
    return settings.claude_model

# Singleton client
_client: AsyncAnthropic | None = None

# ── Rate-limit semaphore ────────────────────────────────────────────────────
# Limit concurrent Anthropic API calls to avoid HTTP 429 rate-limit errors
# when parallel workflow steps fire simultaneous requests via asyncio.gather().
# Tune upward if your API tier allows more concurrent requests.
#
# Lazy-initialized: asyncio.Semaphore binds to the running event loop, so we
# create it on first use to ensure it belongs to the correct loop (important
# for testing where event loops are recreated per test).
API_SEMAPHORE_LIMIT = 3
_api_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Get or create the API rate-limit semaphore for the current event loop."""
    global _api_semaphore
    if _api_semaphore is None:
        _api_semaphore = asyncio.Semaphore(API_SEMAPHORE_LIMIT)
    return _api_semaphore

# ── Token budget tracking (D-01, ATLAS-5) ──────────────────────────────────
TOKEN_BUDGET = 500_000

# Contextvar set by workflow engine before executing steps
_current_workflow_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "_current_workflow_id", default=None
)

# Per-workflow cumulative token usage
_workflow_token_usage: dict[int, int] = {}


class TokenBudgetExceededError(Exception):
    """Raised when a workflow exceeds its per-workflow token budget."""


def set_workflow_context(workflow_run_id: int) -> None:
    """Set the current workflow context for token tracking."""
    _current_workflow_id.set(workflow_run_id)
    _workflow_token_usage.setdefault(workflow_run_id, 0)


def get_workflow_token_usage(workflow_run_id: int) -> int:
    """Get cumulative token usage for a workflow."""
    return _workflow_token_usage.get(workflow_run_id, 0)


def clear_workflow_context(workflow_run_id: int) -> None:
    """Clear workflow context and token tracking."""
    _current_workflow_id.set(None)
    _workflow_token_usage.pop(workflow_run_id, None)


def _track_token_usage(response) -> None:
    """Track token usage from a Claude API response.

    If a workflow context is active, adds usage to cumulative total
    and raises TokenBudgetExceededError if budget is exceeded.
    """
    wf_id = _current_workflow_id.get()
    if wf_id is None:
        return

    usage = response.usage
    tokens_used = usage.input_tokens + usage.output_tokens
    _workflow_token_usage[wf_id] = _workflow_token_usage.get(wf_id, 0) + tokens_used

    logger.info(
        "Claude API tokens: +%d (cumulative: %d / %d) for workflow %d",
        tokens_used,
        _workflow_token_usage[wf_id],
        TOKEN_BUDGET,
        wf_id,
    )

    if _workflow_token_usage[wf_id] > TOKEN_BUDGET:
        raise TokenBudgetExceededError(
            f"Token budget exceeded ({_workflow_token_usage[wf_id]:,} / "
            f"{TOKEN_BUDGET:,} tokens) for workflow {wf_id}"
        )


def get_client() -> AsyncAnthropic:
    """Get or create the singleton AsyncAnthropic client."""
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def call_claude(
    system_prompt: str,
    user_prompt: str,
    response_model: Type[T],
    model: str | None = None,
    max_tokens: int = 8192,
    temperature: float = 0.0,
) -> T:
    """Call Claude and parse the response into a Pydantic model.

    Uses content/instruction separation: system_prompt contains instructions,
    user_prompt contains the data to analyze (wrapped in XML delimiters).

    Retries once on parse failure.

    Args:
        system_prompt: Static instructions (no user data — INV-AI-01).
        user_prompt: Data to analyze, wrapped in XML tags.
        response_model: Pydantic model to validate response into (INV-AI-03).
        model: Claude model to use. Defaults to settings.claude_model.
        max_tokens: Max response tokens.
        temperature: Sampling temperature.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ValueError: If Claude response cannot be parsed after retry.
    """
    client = get_client()
    model = resolve_model_id(model)

    for attempt in range(2):  # 1 retry on parse failure
        sem = _get_semaphore()
        if sem.locked():
            logger.info("API semaphore full, waiting for a slot...")
        async with sem:
            logger.info("API call starting (semaphore acquired)")
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                timeout=settings.claude_timeout,
            )

        # Track token usage (D-01, ATLAS-5)
        _track_token_usage(response)

        text = response.content[0].text

        # Try to extract JSON from the response
        try:
            # Handle markdown-wrapped JSON
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                json_str = text.strip()

            data = json.loads(json_str)
            return response_model.model_validate(data)
        except Exception as e:
            # INV-AI-06: Do not log raw API response or API keys
            if attempt == 0:
                logger.warning(
                    "Parse failed (attempt 1), retrying: %s",
                    str(e)[:200],
                )
                # Add retry instruction to user prompt
                user_prompt = (
                    f"{user_prompt}\n\n"
                    "IMPORTANT: Your previous response could not be parsed as JSON. "
                    f"Please return ONLY valid JSON matching this schema: "
                    f"{response_model.model_json_schema()}"
                )
            else:
                logger.error("Parse failed after retry: %s", str(e)[:200])
                raise ValueError(
                    f"Failed to parse Claude response as "
                    f"{response_model.__name__}: {str(e)[:200]}"
                )

    # Should never reach here, but satisfy type checker
    raise ValueError("Unexpected code path in call_claude")


async def call_claude_raw(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_tokens: int = 16384,
    temperature: float = 0.0,
) -> str:
    """Call Claude and return raw text response (for markdown report generation).

    Args:
        system_prompt: Static instructions.
        user_prompt: Data to analyze.
        model: Claude model to use. Defaults to settings.claude_model.
        max_tokens: Max response tokens.
        temperature: Sampling temperature.

    Returns:
        Raw text response from Claude.
    """
    client = get_client()
    model = resolve_model_id(model)

    sem = _get_semaphore()
    if sem.locked():
        logger.info("API semaphore full, waiting for a slot...")
    async with sem:
        logger.info("API call starting (semaphore acquired)")
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=settings.claude_timeout,
        )

    # Track token usage (D-01, ATLAS-5)
    _track_token_usage(response)

    return response.content[0].text
