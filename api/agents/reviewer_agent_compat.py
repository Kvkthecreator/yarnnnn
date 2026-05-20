"""Compatibility helpers for invoke_reviewer() callers — ADR-256.

Thin adapters so existing callers (review_proposal_dispatch, reviewer_reflection,
invocation_dispatcher, chat.py) can work with ReviewerOutput without large rewrites.
"""
from __future__ import annotations
from typing import Any


def _normalize_reflection_proposals(proposals_raw: list) -> list:
    """Normalize raw ReturnVerdict proposals list into the canonical
    proposal shape (change_type, target_file, reasoning, evidence,
    new_content, plus optional fields).

    Per ADR-261 D6 the reflection executor is no longer a deterministic
    Python service (back_office.reviewer_reflection deleted) — the
    morning-reflection recurrence's prompt now directs the Reviewer to
    produce these proposals directly via WriteFile + ProposeAction.
    The normalizer is preserved as a typing helper."""
    normalized = []
    for p in proposals_raw:
        if not isinstance(p, dict):
            continue
        normalized.append({
            "change_type": p.get("change_type", "no_change"),
            "target_file": p.get("target_file", ""),
            "reasoning": (p.get("reasoning") or "").strip(),
            "evidence": (p.get("evidence") or "").strip(),
            "new_content": p.get("new_content") or "",
            "duration_hours": p.get("duration_hours"),
            "reason": p.get("reason") or "",
            "action_type": p.get("action_type") or "",
            "proposal_inputs": p.get("proposal_inputs") or "",
        })
    return normalized


def output_to_review_decision(output: dict | None) -> dict | None:
    """Adapt ReviewerOutput to the dict shape review_proposal_dispatch expects.

    Maps verdict → decision for the approve/reject/defer routing in
    _run_ai_reviewer().

    ADR-296 v2 D3 removed the FireInvocation-directive extraction
    block — Reviewer no longer self-invokes via directive-fire of
    upstream recurrences; the directives mechanism (per
    review_proposal_dispatch._execute_reviewer_directives) now only
    carries `write_file` + `clarify` actions, and those are emitted
    by the Reviewer's tool calls during the loop, not derived from
    actions_taken here.
    """
    if output is None:
        return None
    verdict = output.get("verdict", "")
    # Map stand_down → defer (no action warranted, queue for human)
    decision = "defer" if verdict == "stand_down" else verdict
    if decision not in ("approve", "reject", "defer"):
        return None

    return {
        "decision": decision,
        "reasoning": output.get("reasoning", ""),
        "confidence": output.get("confidence", "low"),
    }
