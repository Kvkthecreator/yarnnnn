"""
Task Deliverable Inference — ADR-149 Phase 5

Reads task memory/feedback.md → infers user preferences → merges into
DELIVERABLE.md "User Preferences (inferred)" section.

Same pattern as context_inference.py (ADR-144) but scoped to task deliverable
quality. TP triggers this after feedback accumulates — not mechanical, judgment-based.

Two signal sources feed this inference:
  1. User feedback (source: user_edit, user_conversation) — what the user corrected
  2. TP evaluation (source: evaluation) — what TP assessed as gaps

Both are read equally. The inference distills patterns into structured preferences
that shape future output quality.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

INFERENCE_MODEL = "claude-sonnet-4-20250514"

DELIVERABLE_INFERENCE_PROMPT = """You are updating a task's deliverable specification based on accumulated feedback.

Read the feedback entries below. Each entry is a user correction or a system evaluation.
Identify PATTERNS — recurring preferences, repeated corrections, quality expectations.

Update ONLY the "## User Preferences (inferred)" section of the deliverable spec.
Preserve ALL other sections exactly as they are (Expected Output, Expected Assets,
Quality Criteria, Audience).

RULES:
- Each preference should cite which feedback entry produced it
- Remove preferences that are contradicted by newer feedback
- Maximum 10 preferences (prioritize most-cited patterns)
- Be specific: "executive summary ≤3 sentences" not "keep it concise"
- Include both positive patterns (things to keep doing) and negative (things to stop)
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

    # Read feedback.md
    feedback = await tw.read("memory/feedback.md")
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
        anthropic = get_anthropic_client()
        response = anthropic.messages.create(
            model=INFERENCE_MODEL,
            max_tokens=2000,
            system=DELIVERABLE_INFERENCE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        updated_content = response.content[0].text.strip()

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
