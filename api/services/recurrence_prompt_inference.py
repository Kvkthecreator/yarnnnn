"""
Recurrence-Prompt Inference — ADR-149 Phase 5, updated ADR-181, ADR-261.

Reads a recurrence's accumulated feedback.md → infers user preferences →
proposes a refined prompt. YARNNN triggers this after feedback accumulates;
the operator confirms before the prompt is updated via Schedule(action='update').

Per ADR-261 D1 the recurrence's ``prompt`` is the entire output spec —
there is no separate DELIVERABLE.md. So inference is prompt-refinement,
not section-merge inference.

Three signal sources feed this (ADR-181 source-agnostic layer):
  1. User feedback (source: user_edit, user_conversation)
  2. YARNNN evaluation (source: evaluation)
  3. System verification (source: system_verification)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

INFERENCE_MODEL = "claude-sonnet-4-6"

PROMPT_INFERENCE_SYSTEM = """You are refining a recurrence's prompt based on accumulated feedback.

A recurrence is `{slug, schedule, prompt}` (ADR-261 D1). The Reviewer reads
the prompt at fire time and acts on it. The prompt encodes:
  - what the work is (intent)
  - what good output looks like (quality bar)
  - which substrate to read and write (scope)
  - any operator preferences (tone, format, audience)

Read the feedback below. Entries come from three sources (ADR-181):
  - User feedback (source: user_conversation, user_edit) — direct corrections
  - Reviewer evaluation (source: evaluation) — quality assessment
  - System verification (source: system_verification) — deterministic checks

Identify recurring patterns and translate them into refined prompt language.

RULES:
  - Preserve the prompt's core intent. Refine, don't rewrite from scratch.
  - Add inline guidance where feedback shows a recurring miss.
  - Prefer short, specific clauses over long prose.
  - If a preference is one-off (1 entry), do NOT add it. Wait for a pattern.
  - If feedback contradicts an earlier addition, remove the addition.
  - Maximum 25% length growth vs the existing prompt — if you'd grow more,
    the prompt has accumulated drift; collapse weaker clauses to make room.

OUTPUT: Return the COMPLETE refined prompt only. No commentary, no markdown
code fence. Just the prompt body."""


async def infer_recurrence_prompt(
    client,
    user_id: str,
    slug: str,
) -> Optional[str]:
    """Read recurrence prompt + feedback → return refined prompt, or None.

    Returns None when:
      - the recurrence doesn't exist
      - feedback has fewer than 2 entries (insufficient signal)
      - inference produces invalid output

    Caller is responsible for confirming with the operator and routing the
    update through ``Schedule(action='update', changes={'prompt': ...})``.
    """
    from services.anthropic import get_anthropic_client
    from services.conventions import report_feedback_path
    from services.recurrence import walk_workspace_recurrences
    from services.workspace import UserMemory

    recurrences = walk_workspace_recurrences(client, user_id)
    rec = next((r for r in recurrences if r.slug == slug), None)
    if rec is None:
        logger.info(f"[PROMPT_INFERENCE] No recurrence for {slug}")
        return None

    existing_prompt = rec.prompt
    if not existing_prompt or not existing_prompt.strip():
        logger.info(f"[PROMPT_INFERENCE] Recurrence {slug} has empty prompt — skipping")
        return None

    feedback_path = report_feedback_path(slug)
    relative = feedback_path[len("/workspace/"):]
    um = UserMemory(client, user_id)
    feedback = await um.read(relative)
    if not feedback or len(feedback.strip()) < 80:
        logger.info(f"[PROMPT_INFERENCE] No feedback entries for {slug}")
        return None

    entries = re.findall(r"^## ", feedback, re.MULTILINE)
    if len(entries) < 2:
        logger.info(
            f"[PROMPT_INFERENCE] Only {len(entries)} feedback entries for {slug} — skipping"
        )
        return None

    user_message = (
        f"CURRENT PROMPT:\n{existing_prompt}\n\n"
        f"ACCUMULATED FEEDBACK ({len(entries)} entries):\n{feedback[:6000]}"
    )

    try:
        anthropic_client = get_anthropic_client()
        response = await anthropic_client.messages.create(
            model=INFERENCE_MODEL,
            max_tokens=2000,
            system=PROMPT_INFERENCE_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )
        refined = response.content[0].text.strip()

        try:
            from services.platform_limits import record_token_usage
            from services.supabase import get_service_client
            record_token_usage(
                get_service_client(),
                user_id=user_id,
                caller="inference",
                model=INFERENCE_MODEL,
                input_tokens=getattr(response.usage, "input_tokens", 0),
                output_tokens=getattr(response.usage, "output_tokens", 0),
                metadata={"slug": slug, "inference_type": "recurrence_prompt"},
            )
        except Exception as _e:
            logger.warning(f"[TOKEN_USAGE] prompt_inference record failed: {_e}")

        if not refined or len(refined) < 50:
            logger.warning(
                f"[PROMPT_INFERENCE] Inference produced insufficient content for {slug}"
            )
            return None

        # Bound growth — abort if the LLM ignored the 25% growth rule.
        if len(refined) > int(len(existing_prompt) * 1.6):
            logger.warning(
                f"[PROMPT_INFERENCE] Refined prompt for {slug} grew >60% — discarding"
            )
            return None

        logger.info(
            f"[PROMPT_INFERENCE] Refined prompt for {slug} from {len(entries)} feedback entries"
        )
        return refined

    except Exception as e:
        logger.error(f"[PROMPT_INFERENCE] Inference failed for {slug}: {e}")
        return None


__all__ = ["infer_recurrence_prompt"]
