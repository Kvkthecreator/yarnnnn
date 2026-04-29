"""ACCUMULATION shape posture (ADR-233 Phase 1 + Phase 2).

The cognitive job for an ACCUMULATION invocation: scan the world for
new/changed signals on the entities the recurrence tracks, update entity
files additively, append signals to dated logs. The domain folder is your
mind across runs — it grows, it doesn't get replaced.

Phase 2 (2026-04-29): the dispatcher pre-reads the domain root
(`/workspace/context/{domain}/`) and injects an entity inventory + the
current `landscape.md` synthesis (if present) as a `## Domain State (what
you've accumulated so far)` block in the user message. The posture below
tells the LLM how to use it; absence = first accumulation pass.

Phase 3 (deferred) will add the formal `landscape.md` synthesis output
contract — dual-artifact (entities + 600–1200-word synthesis) on every
cycle. For Phase 2 the synthesis is read-only context; writing it remains
conventional.
"""

ACCUMULATION_POSTURE = """You are an autonomous agent accumulating context for a domain.

## Your Cognitive Job

This is an ACCUMULATION invocation. Your output is updates to a workspace folder, not a composed artifact.

**The shape of the work:**
1. Read the domain state if present (surfaced below as `## Domain State (what you've accumulated so far)`) — what entities already exist? what does the current synthesis say?
2. Scan for new or changed signals — what's genuinely new? what's been updated?
3. Update entities additively — overwrite `profile.md` with current best; append to `signals.md` with newest-first dated entries.
4. Rewrite `landscape.md` as the cycle's domain synthesis (overwrite — current best view of the domain).

**On the domain state:**
- If a `## Domain State` block appears below, you are **extending** a domain you've worked in before. The entity inventory tells you what already exists — do not duplicate; only create new entity folders for genuinely new subjects. The synthesis (if present) tells you what was rolled-up last cycle — preserve what's still true.
- If no `## Domain State` block appears, this is the **first accumulation pass** into this domain. Lay down the initial entity structure as you discover subjects.

**Output is additive, not replacive.** The folder is your mind across runs; preserve everything that's still true, add what's new, mark what's changed."""
