"""The ask-builder — ADR-360 D2.

A YARNNN wake is a present-tense ASK, not standing-state framing. For
cadence-fired *owed-output* recurrences (the case with no external event to
raise the ask — e.g. an author's weekly scene), the schedule must fire an
IMPERATIVE ("compose this week's scene now"), not a stored situation-framing
prompt ("assess the operation against its mandate"). The six-probe falsification
arc proved the difference is decisive: framing defers, imperatives produce
(`docs/evaluations/2026-06-24-step3-cron-imperative-VALIDATION.md`).

This module computes, at fire-time, whether a producer recurrence is BELOW its
declared output contract and, if so, returns a present-tense imperative ask to
hand the Reviewer in place of the recurrence's stored prompt. The schedule says
WHEN; the ask-builder says WHAT IS BEING ASKED — and it asks rather than frames.

**The discipline (ADR-360 D2)**: a scheduled ask must be an imperative at
authoring (fire) time, because the clock cannot reason — it delivers verbatim.

Opt-in + program-agnostic (ADR-222: kernel names the category, the bundle names
the instance): a recurrence declares itself a producer via
`options: {produces_owed_output: true}` in `_recurrences.yaml`. The kernel does
not hardcode any program noun ("scene", "trade"); it reads the declared
`kind`/`cadence` from `_expected_output.yaml` and the produced-count from the
operation output tree, and composes a category-neutral imperative.

DP19-aligned: a bounded substrate read (one indexed COUNT + the already-declared
contract), NOT LLM-time state derivation. Carries the ADR-359 `_compute_occasion_fact`
computation, repurposed from "a header among twenty" into "the ask itself".
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# The kernel convention for a produced owed-output artifact: per-entity content.md
# under the operation output tree. Program-agnostic — both bundles ship
# operation/{domain}/{slug}/content.md. (ADR-231 D2 natural-home paths.)
_PRODUCED_ARTIFACT_GLOB = "/workspace/operation/%/content.md"

# Governance file declaring the output contract (ADR-345).
_EXPECTED_OUTPUT_PATH = "/workspace/governance/_expected_output.yaml"


async def count_produced_artifacts(client: Any, user_id: str) -> Optional[int]:
    """Count produced owed-output artifacts under the operation output tree.

    Returns the count, or None on query failure (caller degrades to "no ask"
    rather than asserting a possibly-wrong gap).
    """
    try:
        res = (
            client.table("workspace_files")
            .select("path", count="exact")
            .eq("user_id", user_id)
            .like("path", _PRODUCED_ARTIFACT_GLOB)
            .execute()
        )
        return res.count if res.count is not None else len(res.data or [])
    except Exception as exc:
        logger.warning(
            "[ASK_BUILDER] produced-count query failed for user=%s: %s",
            user_id[:8], exc,
        )
        return None


def _parse_contract(expected_output_yaml: str) -> tuple[str, str]:
    """Parse (kind, delivery_cadence) from _expected_output.yaml. Tolerant:
    a parse miss degrades to generic labels — this is a fact for the ask, not a
    gate."""
    import yaml as _yaml

    kind = ""
    cadence = ""
    try:
        parsed = _yaml.safe_load(expected_output_yaml) or {}
        eo = parsed.get("expected_output", parsed) if isinstance(parsed, dict) else {}
        if isinstance(eo, dict):
            kind = str(eo.get("kind") or "").strip()
            cadence = str(eo.get("delivery_cadence") or "").strip()
    except Exception as exc:
        logger.warning("[ASK_BUILDER] expected_output parse failed: %s", exc)
    return kind, cadence


def compose_owed_output_ask(kind: str, cadence: str, produced: int) -> str:
    """Compose the present-tense imperative ask for a below-contract producer.

    Category-neutral: the kernel names no program noun — `kind` comes from the
    bundle's declared contract. This is the imperative the clock delivers
    verbatim (ADR-360 D2).
    """
    kind_label = kind or "the declared output"
    cadence_label = f" ({cadence})" if cadence and cadence != "event-driven" else ""

    if produced == 0:
        return (
            f"Produce {kind_label} now.\n\n"
            f"Your Expected Output is {kind_label}{cadence_label} and the corpus is "
            f"empty — this is the first one. Nothing external gates it: the mandate, "
            f"your framework (principles.md), the voice/quality floor, and the "
            f"substrate are all present right now. Author the actual artifact to its "
            f"content.md under /workspace/operation/, status draft.\n\n"
            f"Producing it IS the work of this wake — not a plan to produce, not a "
            f"future fire to schedule, not a readiness check. A future wake would face "
            f"this same empty corpus and same mandate, so deferring is circular: it is "
            f"this wake postponed. If a specific floor rule blocks producing it, name "
            f"that rule — that is the only legitimate non-production close. Otherwise, "
            f"produce it now, then close by naming what you produced."
        )

    # produced > 0: the loop is closing; whether THIS runtime owes another is the
    # Reviewer's judgment against cadence + IS. Still an imperative-leaning ask,
    # but it hands the now-vs-later judgment to the agent (a future wake is
    # legitimate only if it would face a materially different state).
    return (
        f"Assess whether {kind_label}{cadence_label} is owed this runtime, and if so, "
        f"produce it now.\n\n"
        f"You have produced {produced} so far. Whether this runtime owes another is "
        f"your judgment against the delivery cadence and current state — but a future "
        f"wake is legitimate ONLY if it would face a materially different state than "
        f"now (a new beat ready, an external input arrived). If it would not, the "
        f"occasion is now: produce it. If genuinely nothing is owed this period, say "
        f"so plainly — that is a clean close, not a deferral."
    )


async def build_owed_output_ask(
    client: Any,
    user_id: str,
    *,
    produces_owed_output: bool,
    expected_output_yaml: Optional[str] = None,
) -> Optional[str]:
    """Return a present-tense imperative ask for a below/at-contract producer
    recurrence, or None when no ask should replace the recurrence's own prompt.

    Returns None when:
      - the recurrence is not a declared owed-output producer, OR
      - no Expected Output is declared (nothing to be below contract against), OR
      - the produced-count query failed (degrade to the stored prompt rather than
        assert a possibly-wrong gap).

    Args:
        produces_owed_output: the recurrence's `options.produces_owed_output`
            flag (bundle-declared opt-in; kernel reads, never hardcodes).
        expected_output_yaml: the already-loaded contract (passed by callers that
            have it, e.g. the wake envelope) to avoid a re-read; loaded here if
            None.
    """
    if not produces_owed_output:
        return None

    if expected_output_yaml is None:
        try:
            res = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", _EXPECTED_OUTPUT_PATH)
                .limit(1)
                .execute()
            )
            expected_output_yaml = (res.data or [{}])[0].get("content") or ""
        except Exception as exc:
            logger.warning(
                "[ASK_BUILDER] expected_output read failed for user=%s: %s",
                user_id[:8], exc,
            )
            return None

    if not (expected_output_yaml or "").strip():
        return None

    produced = await count_produced_artifacts(client, user_id)
    if produced is None:
        return None

    kind, cadence = _parse_contract(expected_output_yaml)
    ask = compose_owed_output_ask(kind, cadence, produced)
    logger.info(
        "[ASK_BUILDER] built owed-output ask for user=%s (kind=%r produced=%d)",
        user_id[:8], kind or "?", produced,
    )
    return ask


__all__ = [
    "build_owed_output_ask",
    "compose_owed_output_ask",
    "count_produced_artifacts",
]
