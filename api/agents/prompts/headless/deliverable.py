"""DELIVERABLE shape posture (ADR-233 Phase 1).

The cognitive job for a DELIVERABLE invocation: read the deliverable spec,
read the prior output (Phase 2 will inject this directly), identify the
gap between what exists and what the spec requires, and produce only the
gap. Output is **replacive** — the new `output.md` supersedes the prior.

Phase 2 will add a `## Prior Output` section to this posture, sourced via
`recurrence_paths` for the natural-home `/workspace/reports/{slug}/{latest}/`
read. For Phase 1 the posture frames the cognitive job; the prior-output
mechanic is removed from the dispatcher (Phase 1 deletes the goal-mode
branch outright; Phase 2 replaces it on the shape axis).
"""

DELIVERABLE_POSTURE = """You are an autonomous agent producing a recurring deliverable.

## Your Cognitive Job

This is a DELIVERABLE invocation. Your output is a composed artifact a human will read.

**The shape of the work:**
1. Read the deliverable specification — what's the quality target?
2. Read the prior output (if any was produced — surfaced in your gathered context as "Prior Output (latest run)") — what already exists?
3. Identify the gap — what sections need updating because source data changed? what's missing entirely? what's still current and should be preserved?
4. Produce only the gap. The new output supersedes the prior; preserve sections whose source data has not changed.

**Output is replacive, not additive.** The new `output.md` is what readers see; sections you don't touch get carried forward verbatim from the prior. This is delta generation."""
