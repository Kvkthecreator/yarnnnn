"""
Task Deliverable Inference — ADR-149 Phase 5, updated ADR-181.

Reads task feedback.md → infers user preferences → merges into
DELIVERABLE.md "User Preferences (inferred)" section.

Same pattern as context_inference.py (ADR-144) but scoped to task deliverable
quality. TP triggers this after feedback accumulates — not mechanical, judgment-based.

Three signal sources feed this inference (ADR-181: source-agnostic layer):
  1. User feedback (source: user_edit, user_conversation) — what the user corrected
  2. TP evaluation (source: evaluation) — what TP assessed as gaps
  3. System verification (source: system_verification) — what deterministic checks flagged

All are read equally. The inference distills patterns into structured preferences
that shape future output quality.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

INFERENCE_MODEL = "claude-sonnet-4-6"

DELIVERABLE_INFERENCE_PROMPT = """You are updating a task's deliverable specification based on accumulated feedback.

Read the feedback entries below. Entries come from three sources (ADR-181):
- **User feedback** (source: user_conversation, user_edit) — direct user corrections
- **TP evaluation** (source: evaluation) — quality assessment against DELIVERABLE.md
- **System verification** (source: system_verification) — deterministic checks (staleness, coverage gaps, low confidence)

All sources are equal signals. Identify PATTERNS — recurring preferences, repeated corrections, quality expectations, structural issues.

Update ONLY the "## User Preferences (inferred)" section of the deliverable spec.
Preserve ALL other sections exactly as they are (Expected Output, Expected Assets,
Quality Criteria, Audience).

RULES:
- Each preference should cite which feedback entry produced it
- Remove preferences that are contradicted by newer feedback
- Maximum 10 preferences (prioritize most-cited patterns)
- Be specific: "executive summary ≤3 sentences" not "keep it concise"
- Include both positive patterns (things to keep doing) and negative (things to stop)
- System verification signals about staleness or coverage indicate structural issues —
  translate them into deliverable preferences (e.g., "ensure all tracked entities have
  data fresher than 14 days" or "minimum 5 entity profiles before synthesis")
- If existing preferences are still valid, keep them
- If a preference has been addressed consistently for 3+ cycles, it can be promoted
  to Quality Criteria (note this, but don't modify Quality Criteria yourself)

OUTPUT: Return the COMPLETE DELIVERABLE.md content with the updated preferences section."""


async def infer_task_deliverable_preferences(
    client,
    user_id: str,
    task_slug: str,
) -> Optional[str]:
    """Read task feedback.md → infer patterns → merge into DELIVERABLE.md.

    Called by TP (via judgment after evaluation, or after feedback accumulation).
    Not a mechanical cron — TP decides when enough signal has accumulated.

    Returns updated DELIVERABLE.md content, or None if insufficient signal.
    """
    from services.task_workspace import TaskWorkspace
    from services.anthropic import get_anthropic_client

    tw = TaskWorkspace(client, user_id, task_slug)

    # Read current DELIVERABLE.md
    existing_deliverable = await tw.read("DELIVERABLE.md")
    if not existing_deliverable:
        logger.info(f"[DELIVERABLE_INFERENCE] No DELIVERABLE.md for {task_slug}")
        return None

    # ADR-181: feedback.md at task root (fallback to memory/feedback.md for migration)
    feedback = await tw.read("feedback.md") or await tw.read("memory/feedback.md")
    if not feedback or feedback.strip() == "# Task Feedback":
        logger.info(f"[DELIVERABLE_INFERENCE] No feedback entries for {task_slug}")
        return None

    # Count feedback entries to decide if there's enough signal
    entries = re.findall(r"^## ", feedback, re.MULTILINE)
    if len(entries) < 2:
        logger.info(f"[DELIVERABLE_INFERENCE] Only {len(entries)} feedback entries for {task_slug} — skipping")
        return None

    # LLM inference
    user_message = (
        f"CURRENT DELIVERABLE SPECIFICATION:\n{existing_deliverable}\n\n"
        f"ACCUMULATED FEEDBACK ({len(entries)} entries):\n{feedback[:6000]}"
    )

    try:
        anthropic_client = get_anthropic_client()
        response = await anthropic_client.messages.create(
            model=INFERENCE_MODEL,
            max_tokens=2000,
            system=DELIVERABLE_INFERENCE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        updated_content = response.content[0].text.strip()

        # ADR-171: Record token spend
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
                metadata={"task_slug": task_slug, "inference_type": "deliverable"},
            )
        except Exception as _e:
            logger.warning(f"[TOKEN_USAGE] deliverable_inference record failed: {_e}")

        if not updated_content or len(updated_content) < 50:
            logger.warning(f"[DELIVERABLE_INFERENCE] Inference produced insufficient content")
            return None

        # Verify the output still has the key sections
        if "## Expected Output" not in updated_content and "## Quality Criteria" not in updated_content:
            logger.warning(f"[DELIVERABLE_INFERENCE] Inference output missing key sections — discarding")
            return None

        # Write updated DELIVERABLE.md
        await tw.write(
            "DELIVERABLE.md",
            updated_content,
            summary=f"Deliverable preferences updated via inference ({len(entries)} feedback entries)",
        )

        logger.info(f"[DELIVERABLE_INFERENCE] Updated DELIVERABLE.md for {task_slug} from {len(entries)} feedback entries")
        return updated_content

    except Exception as e:
        logger.error(f"[DELIVERABLE_INFERENCE] Inference failed for {task_slug}: {e}")
        return None
