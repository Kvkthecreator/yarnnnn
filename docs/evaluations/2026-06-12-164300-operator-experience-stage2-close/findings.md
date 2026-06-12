# Findings — Operator Experience Stage-2 Close (post-P4)

**Scenario:** [`operator-experience-stage1-legibility.yaml`](../scenarios/operator-experience-stage1-legibility.yaml) (same criteria; Stage-2 re-measurement per the scenario's two-stage validation plan, ADR-340 status block)
**Date:** 2026-06-12 · **Commit under evaluation:** `39d2056` (P4) on top of `a3d3625` (Stage-1) / `5c8b06d` (P3)
**Workspace:** `2abf3f96-118b-4987-9d95-40f2d9be9a18` (kvk · alpha-trader active · 2 pending capital proposals at Stage-1 capture)
**Hat:** B (external developer).

## 0. What changed between the stages

P4 (`39d2056`) shipped the Stage-1 evidence-forced set: F1 (two summary rewrites), F2 (Sources chain caption + Autonomy live consequence preview), F3 (one shared proposal labeler across the Home decision slot, chat ProposalCard, and AttentionCenter), and pinned the D6 widget-contract audit finding by gate.

## 1. C2 re-run — consequence legibility: **gap closed at the three measured points**

Re-read of the same surfaces, same inference discipline (surface text only):

- **Sources pane**: the full variant now carries the chain caption — *"What you declare here becomes your agent's perception: each source is fetched on the watch's cadence, distilled into a signal file, and read at every wake — it shapes what your agent notices and what reaches your Queue."* Steps 3–6 of the §7.1 chain, previously invisible, are now stated at the point of the act. A cold operator declaring a source can infer the downstream consequence. **PASS.**
- **Autonomy pane**: the confirm modal — the switch moment, the Night-Shift analog — now appends a **live** line derived from the actual pending queue. Against the Stage-1 substrate (2 pending capital proposals), a switch to `autonomous` reads: static rule copy + *"Right now: 2 pending actions would become eligible to execute without you."* The criterion's exact formulation from Stage-1 F2, shipped as derivation-only (no stored state — verified by gate). **PASS.**
- **Attention rows / decision slot / ProposalCard**: the two live proposals now render *"Submit a trade order · trade-proposal"* (shared labeler) instead of `platform_trading_submit_order · capital · trade-proposal`. Operator-language at the moment of highest consequence. **PASS** — and the consolidation closed a latent drift surface (two parallel label implementations found in the P4 audit are now one module).
- **F1 residue**: Activity now reads "What ran and what it cost — the execution log behind the Feed's story…"; Recurrence reads "What's on the schedule…". Both answer when-to-visit; the C1 PARTIAL rows clear.

**Honest bound:** C2 is an anthropic criterion; this re-run confirms the *surfaces now state the consequence* — whether a real cold operator *absorbs* it is confirmable only by the operator walk (§3). No further machine-side gap is known.

## 2. Closing smoke (machine side): **all green**

```
test_adr340_p4_legibility  22/22   (F1/F2/F3 + D6 pin)
test_adr340_p3_launcher    18/18
test_adr340_p2_settings_fold 51/51
test_adr340_p1_attention   27/27
test_adr338_surface_registry_parity 15/15
test_adr338_runway_launcher 24/24
test_adr338_sources        37/37
test_adr327_phase6_fe      30/30
test_adr297_phase1         148/148
test_adr339_perception_economics 25/25  (concurrent lane, untouched)
tsc --noEmit               clean
```

Known pre-existing, out of this lane: `test_adr312_home_as_composition` 2 FAILs on stale `api/routes/pace.py` assertions (proven present with all ADR-340 work stashed at P2; rot from the ADR-327 pace→budget collapse — needs its own small repair commit).

## 3. Operator walk — the Stage-2 addendum to the Stage-1 §5 checklist

The remaining human-eyes items (added to the Stage-1 walk, all on `39d2056`):

6. **Sources pane**: the chain caption renders above the watch editor.
7. **Autonomy pane**: click a different level → the confirm modal shows the "Right now: …" line reflecting your actual pending count.
8. **Attention bell / Home decision slot**: the two trade proposals read "Submit a trade order", not the primitive slug.
9. **Launcher Utilities group**: Activity + Recurrence summaries now answer "when would I open this?"

## 4. Disposition — program close

- **ADR-340 P1–P4: complete.** Both validation stages executed; machine-side criteria all PASS; the anthropic halves await the operator walk (checklists in Stage-1 §5 + §3 above).
- **Remaining open (recorded in ADR-340 status):** Queue window-vs-routed fate (evidence-driven, deferred); program-weighted Home slot bindings under the widget contract (program-bundle work, not kernel); the pre-existing ADR-312 gate rot (separate repair).
- **Pattern note for future evals:** the measure → derive → re-measure loop (Stage 1 forcing P4, Stage 2 confirming) closed in one day with every finding traceable from criterion → receipt → fix → gate. This is the §7.4 pattern working as designed; recommend it as the default shape for operator-experience changes.
