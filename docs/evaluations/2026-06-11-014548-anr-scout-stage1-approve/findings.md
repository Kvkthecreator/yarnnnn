# Findings — anr-scout Stage-1 completion (operator approvals)

**Verdict: PASS with one REAL FINDING.** All five approvals executed as `operator`-attributed revisions; the post-approval read-back correctly reported the constitution live, named AUTONOMY as still-operator-territory, and named artist intake as the unblock. Stage 1 complete.

## Receipts
- 5 operator revisions 01:45:51–01:45:54: MANDATE (1761 ch), BRAND (1663), IDENTITY (765), principles (**0 ch — see finding**), standing_intent (1580).
- judgment_log carries the approval trail (`reviewer:human:{uuid}` attribution — the two-embodiments shape).

## FINDING 1 (real): the seat's queued principles proposal carried NULL content
Proposal `226e125c` had empty `inputs.content` (its four siblings carried 765–1761 chars). The approval executed faithfully → wrote an **empty** `persona/principles.md`. Downstream: the Stage-2 bundle fork correctly classified empty-as-skeleton and re-applied the bundle template — which initially looked like a fork clobber but was not. Two Hat-A recommendations:
1. **Seat-side**: a WriteFile tool call lost its content arg in a 5-write round (likely arg truncation under parallel tool calls). Worth a regression probe.
2. **Kernel-side hardening**: the proposal gate should **fail-fast a WriteFile proposal with missing/empty content at creation time** — a content-less write is malformed; executing it as an empty overwrite is silent data loss with an approval receipt.
Repair: operator re-authored principles merging bundle structure + the declared A&R framework (revision `dce79580`).

## Observation
- judgment_log writes each approval entry TWICE (dual-write smell — two revisions per approval at 01:45:51–53). Hat-A hygiene item.
