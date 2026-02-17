"""Visser macro regime analyst -- calls Claude with the Visser system prompt.

Content/instruction separation (INV-AI-01): system prompt = instructions,
user message = data wrapped in XML tags.
"""

import logging

from app.services.persona.persona_prompts import get_persona_prompt
from app.services.claude_client import call_claude_raw

logger = logging.getLogger(__name__)

# Structured-mode instruction appended to the user message
_STRUCTURED_INSTRUCTION = (
    "Address the question above directly using the context provided. "
    "Structure your response using your standard output sections "
    "(Regime Assessment, Thesis Compatibility, Green Marbles, Tailwinds, "
    "Headwinds, Kill Condition, Conviction), but ensure each section "
    "specifically answers aspects of the question rather than providing "
    "a generic template."
)

# Freeform-mode instruction — open-ended, no forced sections
_FREEFORM_INSTRUCTION = (
    "Provide your macro regime assessment. Explore freely — structure your "
    "response however best serves the analysis."
)


async def analyze_visser(
    context: str,
    user_prompt: str,
    mode: str = "structured",
) -> dict:
    """Run Visser macro regime analysis.

    Args:
        context: Investment thesis and data context.
        user_prompt: The specific question or thesis to evaluate.
        mode: "structured" or "freeform".

    Returns:
        Structured dict with Visser's analysis fields and raw narrative.
    """
    instruction = _STRUCTURED_INSTRUCTION if mode == "structured" else _FREEFORM_INSTRUCTION
    user_message = (
        "<context>\n"
        f"{context}\n"
        "</context>\n\n"
        "<question>\n"
        f"{user_prompt}\n"
        "</question>\n\n"
        f"{instruction}"
    )

    system_prompt = get_persona_prompt("visser", mode)
    raw = await call_claude_raw(system_prompt=system_prompt, user_prompt=user_message)

    return {
        "regime_classification": None,
        "green_marbles_assessment": None,
        "kill_conditions": [],
        "overall_verdict": None,
        "raw_narrative": raw,
    }
