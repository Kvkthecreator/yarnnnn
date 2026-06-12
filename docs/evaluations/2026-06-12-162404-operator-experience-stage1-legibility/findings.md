# Findings — Operator Experience Stage-1 Legibility (post-P3, pre-P4)

**Scenario:** [`operator-experience-stage1-legibility.yaml`](../scenarios/operator-experience-stage1-legibility.yaml)
**Date:** 2026-06-12 · **Commit under evaluation:** `5c8b06d` (P1 `e35a20e` + P2 `be6944d` + P3 `5c8b06d`)
**Workspace:** `2abf3f96-118b-4987-9d95-40f2d9be9a18` (kvk · alpha-trader active · trading connection active)
**Hat:** B (external developer). Findings recommend system-side changes; fixes land in Hat-A canon (ADR-340 P4).

## 0. Substrate receipts (live, read-only)

```
pending_proposals: 2
  65dd6969 platform_trading_submit_order capital trade-proposal
  84ea6289 platform_trading_submit_order capital trade-proposal
material_last72h: 17        (session_messages, metadata->>'weight'='material', role != 'user')
balance_usd: 45.0000        (workspaces.owner_id match)
mandate_head: "--- / activated_bundle_version: 2026-05-20.1 / --- / # Mandate — alpha-trader /
               > **Operator**: author this file. Kee…"   (template-state — bundle marker present,
               body still carries the author-here prompt)
connections: trading:active
program-tier surfaces: NONE (alpha-trader SURFACES.yaml declares no surfaces: block → launcher is kernel-only)
registry passthrough: kernel_surface_entries() emits pane_of/launcher_tier verbatim
  (verified: budget → pane_of=settings, pane_group=Governance)
```

At-rest launcher rendering (deterministic: registry × `launcher_tier`):

```
WORKSPACE   Home · Feed · Queue · Files
SYSTEM      System Settings
UTILITIES   Setup · Activity · Recurrence · Agents
(hidden at rest: mandate, principles, identity, budget, autonomy, program, connectors, sources)
```

## 1. C1 — Launcher act-legibility: **PASS, two summary-copy caveats**

The structural criterion holds: the at-rest index is 9 rows, the standing loop is the first group, mirrors are hidden, and the one config door reads as one door. A cold reader of the three group labels gets the act ordering for free (work surfaces → the system → the toolbox). This is the Layer-3 fix the discourse demanded, and it is structurally in place.

Row-level inference read (title + summary alone, no canon knowledge):

| Row | "What act / when to visit" inferable? |
|---|---|
| Home — "The operation, rendered…" | YES (dwell; daily) |
| Feed — "Operator chat surface and multi-actor narrative timeline" | YES (read/converse) |
| Queue — "Pending proposals awaiting Reviewer or operator decision" | YES (decide) — and the attention badge now routes here |
| Files — "Raw substrate browser…" | YES (artifacts) |
| System Settings — "the one os-config door… Sidebar panes" | YES (tune; occasional) |
| Setup — "Guided first-boot sequence…" | YES (pass-through) |
| Agents — "Agent roster…" | YES (reference) |
| **Activity** — "Execution-event log — every wake, every dispatch, every cost" | **PARTIAL** — "wake" and "dispatch" are kernel vocabulary; a cold operator cannot tell this from Feed ("which one tells me what happened?"). The tier demotion mitigates (it reads as a utility), but the summary still speaks mechanism. |
| **Recurrence** — "Recurrences, substrate-event hooks, standing intent, and wake telemetry" | **PARTIAL** — the most mechanism-speaking summary in the index ("substrate-event hooks", "wake telemetry"). A cold operator cannot answer "when would I open this?" |

**Finding F1:** the structural IA passes; the residual confusion the founder reported ("queue, feed, activity, recurrence seem similar") is now concentrated in exactly two summary strings, both in the Utilities tier. Recommendation (Hat-A, cheap, can ride with P4): rewrite the Activity + Recurrence summaries in operator vocabulary ("what ran and what it cost" / "what's on the schedule"). No structural change needed.

## 2. C2 — Consequence legibility: **GAP CONFIRMED, precisely where predicted** (P4 forcing evidence)

Read of the shipped System Settings panes against the §7.1 chain (declare → fetch on cadence → distill to signal → wake envelope → shapes proposals → lands in Queue):

- **Sources pane** (SourcesCard + pane copy): shows the declared list, per-source observed health, and the cadence pointer. Steps 1–2 of the chain are visible; steps 3–6 (the declaration becomes the agent's *perception*, daily, and shapes what reaches the Queue) are not inferable from the surface. Unchanged from the §7.1 diagnosis — expected, since the consequence-preview affordance is P4 scope.
- **Autonomy pane** (AutonomyCard): shows level + confirm-gated switching. NOT inferable: what concretely changes at each level for *this* workspace (e.g., "at `autonomous`, the two trades now pending would have executed without you"). That last formulation is the Night-Shift-style preview P4 should ship — note it can be derived from live substrate (pending proposals × delegation level), no new state.
- **Budget pane** (merged money chip + BudgetCard): the strongest of the three — envelope paired with funds + runway already conveys consequence ("workspace hard-stops at $0" is consequence copy). Closest existing approximation of the target pattern.

**Finding F2:** the consequence-legibility gap is real, bounded, and now *sized*: it is a per-pane preview affordance over already-available substrate (Sources: "this feeds your agent's next wake"; Autonomy: "at level X, these N pending items would auto-execute"; Budget: already approximates it). This is the P4 forcing evidence ADR-340's validation plan reserved. The criterion itself survives the pre-flight audit — it measures a deferred affordance, declared as such; no regression is asserted against P1–P3.

## 3. C3 — Attention routing: **PASS structurally, one vocabulary finding**

Derived AttentionCenter state for the live workspace: badge = 2 pending + unseen-material (≤17 depending on the operator's read cursor); no warning row ($45 ≫ $1 threshold); "Needs your decision" section lists two rows; every row deep-links.

A cold operator CAN tell *that* two things demand them and *where* to decide — the routing criterion holds; the Queue no longer depends on being remembered.

**Finding F3:** the proposal rows render `platform_trading_submit_order · capital · trade-proposal` — the **primitive slug**, mechanism vocabulary at the exact moment of highest consequence. The operator's concept is "a trade wants approval." This is the C2 gap surfacing inside the attention channel. Recommendation (Hat-A): operator-language labels for proposal rows (family + verb-phrase derived from primitive, e.g., "Submit order — trade proposal"), in P4 alongside the queue diff-preview vocabulary (ADR-307 family-shaped rendering already established the pattern).

## 4. C4 — Constitution door: **PASS, honest empty-state confirmed**

kvk's MANDATE.md is template-state (bundle marker + "Operator: author this file"). The band's canonical L2 parse renders the author-CTA branch ("Mandate not yet declared… Author in chat") — honest, since the operator genuinely hasn't authored it — and the ConstitutionLinks trio (Mandate · Principles · Identity) renders in both branches, so all three mirrors are reachable from Home with the launcher tiles gone. The door exists and is honest about the constitution's actual state.

## 5. Stage-1 completion — operator browser walk (required; not machine-evaluable)

The inference reads above are developer-simulated. KVK completes Stage 1 with eyes on `5c8b06d`:

1. **Launcher**: ⌘-open → confirm three groups (Workspace/System/Utilities), 9 rows; type "auto" → Autonomy appears labeled "System Settings pane"; select it → System Settings opens at the Autonomy pane.
2. **System Settings**: sidebar shows General / Perception & transports / Governance / Program; old bookmarks `/budget`, `/sources` redirect into the right pane; Program pane shows lifecycle + "Re-run setup".
3. **Attention**: bell shows badge ≥2; dropdown lists the two trade proposals under "Needs your decision"; row click lands on Queue.
4. **Home band**: "Mandate not yet declared" CTA + the Mandate · Principles · Identity trio; each link opens its mirror window.
5. The felt test (the criterion itself): *from the launcher alone, do you know what to do next and why?*

## 6. Disposition

- **P4 inputs (Hat-A, ADR-340)**: F2 (consequence previews per pane, derivable from live substrate, no new state) + F3 (operator-language proposal labels) + F1 (two Utilities summary rewrites) join the already-ratified P4 scope (Home widget contract). The Home re-derivation should make each slot answer F2's question for its act — that is the same gap at the composition level (ADR-340 D6 already records this).
- **No criterion repair needed** — all four survived the pre-flight audit; C2's deferred-affordance status was declared before measurement.
- Stage 2 (post-P4) re-runs C2 with the previews shipped + the closing smoke.
