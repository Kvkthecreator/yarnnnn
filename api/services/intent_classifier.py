"""Intent classifier — ADR-252 D1.

Classifies each user chat message as either:
  - 'execution': imperative commands with no judgment content
  - 'judgment':  requests that invoke the operator's judgment character

This is a Haiku gate (~200 input tokens, ~$0.0003/call) that routes
before any substantive LLM work. Falls back to 'judgment' on any failure —
safe default (Reviewer speaking when uncertain is never wrong).

The classifier does NOT replace judgment: it routes. If it mislabels a
judgment question as execution, the System Agent narrates thinly and
the operator rephrases — one cheap misrouted turn, not a missed verdict.

Caller: api/routes/chat.py response_stream() before dispatching the turn.
"""

from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

IntentClass = Literal["execution", "judgment"]

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_TOKEN_CALLER = "intent-classifier"

_CLASSIFIER_SYSTEM = """\
You classify operator messages into exactly one of two intent classes.

execution — the operator wants the system to do something mechanically:
  fire a recurrence, pause a recurrence, read a file, show a list,
  check a status, tell me what happened, summarize results, run something.
  Examples: "Fire signal-evaluation", "Pause the trading recurrence",
  "Show me today's trades", "What happened overnight?",
  "Read my AUTONOMY.md", "List my recurrences".

judgment — the operator wants their judgment character's opinion, assessment,
  or reasoning on their behalf. This includes: strategy questions,
  should-I questions, what-do-you-think questions, principle-application
  questions, configuration decisions with behavioral consequences,
  review-of-results questions where evaluation is the point.
  Examples: "What do you think about holding NVDA?",
  "Is this trade consistent with my principles?",
  "Should I widen my ceiling to $2000?",
  "Review what the signal evaluation found",
  "What does Simons think about the current setup?",
  "Is this portfolio positioning right?".

Respond with exactly one word: execution or judgment. Nothing else.\
"""


async def classify_intent(
    user_message: str,
    *,
    client: object | None = None,
    user_id: str | None = None,
) -> IntentClass:
    """Classify a user message as 'execution' or 'judgment'.

    Uses Haiku for near-zero cost (~$0.0003/call). Falls back to 'judgment'
    on any failure — the safe default.

    Args:
        user_message: the raw operator message text.
        client: Supabase client for token usage recording (optional).
        user_id: for token usage recording (optional).

    Returns:
        'execution' or 'judgment'.
    """
    if not user_message or not user_message.strip():
        return "execution"  # empty message → no judgment content

    try:
        from services.anthropic import chat_completion_with_tools

        response = await chat_completion_with_tools(
            messages=[{"role": "user", "content": user_message.strip()[:500]}],
            system=_CLASSIFIER_SYSTEM,
            tools=[],  # no tools — pure text response
            model=_HAIKU_MODEL,
            max_tokens=5,
            tool_choice={"type": "auto"},
        )

        # Extract text from response
        text = ""
        if hasattr(response, "content"):
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text
        text = text.strip().lower()

        # Record token usage if client provided
        if client and user_id:
            try:
                from services.platform_limits import record_token_usage
                usage = getattr(response, "usage", None) or {}
                input_t = getattr(usage, "input_tokens", 0) or 0
                output_t = getattr(usage, "output_tokens", 0) or 0
                record_token_usage(
                    client,
                    user_id=user_id,
                    caller=_TOKEN_CALLER,
                    model=_HAIKU_MODEL,
                    input_tokens=input_t,
                    output_tokens=output_t,
                )
            except Exception:
                pass  # non-fatal

        if text.startswith("execution"):
            return "execution"
        if text.startswith("judgment"):
            return "judgment"

        # Ambiguous response — safe default
        logger.warning(
            "[INTENT_CLASSIFIER] ambiguous response %r for message %.50r — defaulting to judgment",
            text,
            user_message,
        )
        return "judgment"

    except Exception as exc:
        logger.warning(
            "[INTENT_CLASSIFIER] classification failed for %.50r: %s — defaulting to judgment",
            user_message,
            exc,
        )
        return "judgment"
