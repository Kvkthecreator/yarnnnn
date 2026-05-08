"""Compatibility helpers for invoke_reviewer() callers — ADR-256.

Thin adapters so existing callers (review_proposal_dispatch, reviewer_reflection,
invocation_dispatcher, chat.py) can work with ReviewerOutput without large rewrites.
"""
from __future__ import annotations
from typing import Any


def _normalize_reflection_proposals(proposals_raw: list) -> list:
    """Normalize raw ReturnVerdict proposals list into the shape
    reflection_writer.apply_reflection_writes() expects."""
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
    _run_ai_reviewer(). Preserves directives as actions_taken entries
    with action=fire_invocation shape so _execute_reviewer_directives
    still works.
    """
    if output is None:
        return None
    verdict = output.get("verdict", "")
    # Map stand_down → defer (no action warranted, queue for human)
    decision = "defer" if verdict == "stand_down" else verdict
    if decision not in ("approve", "reject", "defer"):
        return None

    result: dict = {
        "decision": decision,
        "reasoning": output.get("reasoning", ""),
        "confidence": output.get("confidence", "low"),
    }

    # Carry any FireInvocation actions_taken as directives
    directives = [
        {"action": "fire_invocation", "slug": a.get("slug", ""), "reason": a.get("reason", "")}
        for a in (output.get("actions_taken") or [])
        if a.get("tool") == "FireInvocation"
    ]
    if directives and decision == "defer":
        result["directives"] = directives

    return result
