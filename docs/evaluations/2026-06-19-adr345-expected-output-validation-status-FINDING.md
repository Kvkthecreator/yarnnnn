# Finding — ADR-345 Expected Output: code+canon shipped & verified; live behavioral validation blocked on a topped-up clean author workspace

**Date**: 2026-06-19
**Hat**: B (validation status, honest)
**Subject**: ADR-345 (Expected Output as the workspace's declared output contract + autonomy-as-witness reframe), commit `4e47836`, deployed `dep-d8q82f3rjlhs73de9co0` (live).

---

## What is verified (shipped, gated, deployed)

The **mechanism** is verified end-to-end at the code + canon layer:

- `governance/_expected_output.yaml` reads into the wake envelope (`reviewer_envelope.py::_UNIVERSAL_ENVELOPE_DECLS` → `expected_output_yaml`) + the `ReviewerContext` TypedDict + renders in the wake message (`reviewer_agent.py::_build_user_message`) — confirmed by an import/wiring assertion.
- Both bundle sidecars are valid YAML with the `{kind, delivery_cadence, bar}` schema (trader: trade / per-signal-when-fires; author: piece / event-driven) — confirmed by a yaml.safe_load + schema assertion.
- Gates green: frame-collapse 6/6, stewardship 16/16 (floor discipline intact), bundle-conformance 16/16.
- Canon: GLOSSARY v2.8 (Rhythm · Expected Output · Witness dial), FOUNDATIONS DP30 amended (declared-then-derive + Rhythm⟂Expected-Output), both AUTONOMY.md flipped ceiling→witness, both `_workspace_guide.md` trifecta→four-declarations (also cleared stale `_pace.yaml` naming).

The **autonomy-as-witness reframe is verified by inspection** (`permission.py::resolve_permission`): the gate runs after the Reviewer decides; QUEUE routes to `action_proposals` ("operator approves later"), never blocks the agent's work. The reframe is prose-only and correct against the code.

## What is NOT yet verified (the live behavioral proof) — and why

**Claim to validate**: on a *fresh, clean, healthy* author workspace with a **declared** Expected Output (real delivery-cadence) + `autonomous`, the Reviewer works the job (authors its own compose organ + produces at the declared cadence) **without** the spurious "what cadence?" Clarify the contaminated yarnnn-author emitted (the missing-contract symptom).

**Status: BLOCKED on workspace availability, not on the design.** Three candidate author workspaces, none viable:

| Workspace | State | Why not viable |
|---|---|---|
| `yarnnn-author` (`0b7a852d`) | active, healthy | **Contaminated** — the ADR-343-session publish lives in the revision DAG; the Reviewer reads history (verified 2026-06-18), so it does not perceive true dormancy. A head-state reset does not scrub it. |
| `netflix-script-author` (`23cc7951`) | provisioned, dormant | **Balance exhausted** (`balance_usd: -0.0811`). The addressed wake correctly refuses (`{balance_exhausted: True}` — ADR-171/172 hard-stop-at-zero, *correct* behavior); crons funnel-`skip` for the same reason. Fixture (declared Expected Output `weekly` + autonomous) was set (revs `0162c656`, `88d356f3`) but the wake can't run unfunded. |
| `korea-thriller-shorts` (`ca478643`) | provisioned, dormant | Cron wakes `failed`/skip — same dormant-provisioned-persona class (likely same balance/idle cause). |

The block is **billing/availability** — these are provisioned-but-unfunded alpha personas (ADR-283 step-6), not active operations. Topping up a clean author workspace (a real-money action on an alpha account) closes the gap; that needs operator go-ahead.

## The honest bottom line

ADR-345's **design, code, and canon are complete, gated, and deployed.** The behavioral proof — that a *declared* Expected Output dissolves the missing-contract Clarify under autonomous — is the one outstanding item, and it is blocked purely on having a **funded, clean author workspace**, not on anything in the ADR. The cleanest close: top up `netflix-script-author` (fixture already staged: Expected Output `weekly` scene + autonomous) and re-run the dormancy probe; the read is whether it produces/authors-a-compose-organ against the declared weekly cadence without asking which path to take.

## Receipts

| Claim | Receipt |
|---|---|
| ADR-345 deployed | `dep-d8q82f3rjlhs73de9co0` status=live, commit `4e47836`, 23:39Z |
| Envelope + ReviewerContext + render wired | import assertion: `expected_output_yaml` in `_UNIVERSAL_ENVELOPE_DECLS` + `ReviewerContext.__annotations__` |
| Sidecars valid + schema | yaml.safe_load both; trader=trade/per-signal-when-fires, author=piece/event-driven |
| Gates | frame 6/6, stewardship 16/16, conformance 16/16 |
| netflix fixture staged | `_expected_output.yaml` rev `0162c656` (weekly), `_autonomy.yaml` rev `88d356f3` (autonomous) |
| netflix blocked on balance | addressed-wake response `{balance_exhausted: True, balance_usd: -0.0811}` |
| yarnnn-author contaminated | 2026-06-18 finding — Reviewer reads revision DAG, head-state reset insufficient |
