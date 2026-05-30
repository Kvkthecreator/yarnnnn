# Eval-suite framework update — pre-flight audit

**Date**: 2026-05-30
**Hat**: B (external developer surface — toolchain that probes the system)
**Status**: audit + build (same session, 2026-05-30). This doc front-loaded the gap map; the §3 bridge (C1–C7) + §4 prior-fix were then built in the same session after operator confirmed the four §6 forks (hard-break v2-only / re-prior-only / judgment-first / build-now). The §3 + §4 + §5 sections below are the *as-planned* gap; the build outcome is in §8.
**Scope**: maps the gap between the **Proposed v2 framework** (`EVAL-SUITE-DISCIPLINE.md`, 2026-05-29 rewrite) and the **as-built harness** (`run_eval_suite.py`, `operator_proxy/`), against the ADR-307 worked example that just landed.

> Read order: this doc → `EVAL-SUITE-DISCIPLINE.md` (the target shape) → `../analysis/eval-suite-redesign-from-first-principles-2026-05-29.md` (the reasoning behind the target). This doc is the *delta*: what the target specifies that the harness does not yet do.

---

## §0 One-paragraph state of the world

The eval-suite framework is **a fully-authored v2 spec sitting on top of a fully-v1 harness.** The discipline doc (`EVAL-SUITE-DISCIPLINE.md`) was clean-slate-rewritten 2026-05-29 to drop dimension-scoring in favor of operator-question prose reads; the two v2 suite manifests (`yarnnn-author-judgment.yaml` + `yarnnn-author-responsiveness.yaml`) already exist in the new schema; all 10 referenced scenarios exist. But `run_eval_suite.py` is **still v1** — it pins `SUITE_SCHEMA_VERSION = 1`, *requires* `expected_dimensions` on every eval, renders four-dimension `Pass?` tables with `<!-- TODO -->` cells, and emits a `DRAFT/POPULATED` status. **The v2 manifests cannot load against the v1 runner** (it rejects `eval_suite_schema_version: 2` at line 69 and raises on missing `expected_dimensions` at line 88). The §8 harness change-list (C1–C7) that bridges this is *named but unbuilt*. The framework update is therefore: **build C1–C7, fix one stale canon assumption baked into a suite (ADR-307 withdrew the bounded-mode-falls-through-to-Clarify premise the responsiveness suite cites), and promote the ADR-307 validation script's two disciplines (empty-wake-guard + architecture-shape receipt) into the harness.**

---

## §1 The three layers and their actual state

| Layer | File(s) | Spec'd? | Built? | Gap |
|---|---|---|---|---|
| **Discipline doc** | `EVAL-SUITE-DISCIPLINE.md` | ✅ v2 (2026-05-29 rewrite) | n/a (doc) | None — this is the target |
| **Suite manifests** | `eval-suites/yarnnn-author-{judgment,responsiveness}.yaml` | ✅ v2 schema | ✅ authored | One stale prior (§4) |
| **Scenarios** | `scenarios/author-*.yaml` (10) | ✅ | ✅ all 10 present | None (reused as-is per §7.2.5) |
| **Runner** | `run_eval_suite.py` | spec'd by §8 C1–C6 | ❌ **v1** | The whole bridge (§3) |
| **Precondition enforce** | `requires:`/`setup:` | spec'd by §8 C2/C3 | ⚠️ *partial* | `check_preconditions` + file-absent delete missing (§3) |
| **Proxy client** | `operator_proxy/client.py` | n/a | ✅ + SSE-fix | empty-wake-guard not promoted (§5) |

---

## §2 What is genuinely already in place (don't rebuild)

1. **The SSE-decode fix is live in the client** (`client.py:204–239`). The 2026-05-29 diagnosis — the old parser read only `type=='text'`, which judgment turns never emit, producing a false-empty `text` — is fixed: `send_message` now captures `reviewer_response`, bare `content`, AND legacy `type=='text'` into `text`. Every eval rides this. **Do not touch.**

2. **The setup mechanism C3 builds on exists** (`scenarios.py`): `_write_substrate_with_author` (line 465) writes operator-proxy-attributed revisions via `write_revision`; `_execute_setup_step` (line 200) applies `write_substrate` / `seed_draft` / `flip_frontmatter_field` setup steps. The proxy's `write_substrate` (`client.py:349`) is the same path. **C3's "establish declared files" half is built; only the "delete files declared `absent: true`" half is missing.**

3. **The completion gate works** (`run_eval_suite.py:218–330`): polls `wake_queue` by `dedup_key` (substrate-event wakes) + `execution_events` by `wake_source='addressed'` (addressed wakes) until settled, bounded 600s timeout, graceful partial. This is read-kind-agnostic — it survives the v2 reshape unchanged.

4. **The cost rollup is the one honest number and is correct** (`compose_cost_rollup`, line 394). The per-eval cost attribution already uses a `created_at` window (line 682), which §8 C6 flagged as the fix the d38130e run validated. **C6 is effectively already done** — confirm and keep.

5. **All 10 scenarios exist and are referenced correctly** by the two v2 suites. The suite→scenario boundary is clean (suite adds `requires`/`prior`/`accumulates`; scenario unchanged).

---

## §3 The bridge: §8 C1–C7, audited against the runner

This is the build work. Each row maps a §8 change to its **current as-built state** and the **specific code site**.

| # | Change | As-built now | What's needed |
|---|---|---|---|
| **C1** | Schema v2 load + validate | ❌ `SUITE_SCHEMA_VERSION = 1` (L46); rejects v2 (L69); `load_suite` requires `expected_dimensions` per eval (L88) | Bump to 2; require `read_kind`; accept `requires`/`prior`/`accumulates`/`inherits`; stop requiring `expected_dimensions`; drop `DEFAULT_BUDGET` qualitative floors (`per_eval_usd`/`trace_completeness_floor`/`m6_drift_ceiling`), keep `per_session_usd` |
| **C2** | Pre-flight `requires:` check | ❌ does not exist — runner fires against whatever state exists (the exact c51c44f failure) | New `check_preconditions(user_id, eval_def)`: evaluate each `requires:` against live `workspace_files` (dotted-path YAML `field…equals`, `contains`/`not_contains`, `absent: true`/file-present). On mismatch → do NOT fire; record `{fired: false, reason: precondition_violation}`. **This is the load-bearing structural fix.** |
| **C3** | Pre-flight `setup:` establishment + reset-to-clean | ⚠️ half-built — `_write_substrate_with_author` establishes declared files; **no file-delete for `absent: true`**; **no default reset-to-clean between evals** | Lift a reusable `establish_substrate(user_id, requires, setup)` helper: apply file writes (exists) + DELETE workspace_files where `absent: true` (revision chain preserved per ADR-209). Default reset-to-clean per §3.1 unless `accumulates: true`. |
| **C4** | Rollup → prose scaffold | ❌ `render_session_md` emits four `Pass?`-cell dimension tables + `<!-- TODO -->` (L620–668) | Replace with: §Preconditions table (automated, from C2), per-eval prose-prompt blocks (situation + prior + receipt-pointers, read left blank), §Cost appendix (keep), §Read-state line. Delete `_verdict_pass_marker` (L456), `_format_substrate_inputs_compact` (L521), `_format_eval_shape_compact` (L494), `_shape_aggregate_summary` (L504). |
| **C5** | Read-state replaces DRAFT/POPULATED | ❌ emits `**DRAFT**` (L745) | Emit `## §Read-state` naming what was read (runner: "Read: nothing yet — runner scaffold only"). |
| **C6** | Per-eval cost attribution | ✅ already windowed by `created_at` (L682) | Confirm it's the only path + the §Cost appendix uses it. Near-done. |
| **C7** | README scenario-schema note | ❌ not added | Document `requires:`/`prior:` on the *suite eval entry* (not scenario schema) in README. |

**Sequencing note**: C1 is the unblocker (without it nothing loads). C2+C3 are the load-bearing pair (they make the c51c44f precondition-violation class structurally impossible — the entire reason for the rewrite). C4+C5 are the artifact-shape change (mechanical once C1 lands). C6 is a confirm. C7 is doc.

---

## §4 The stale canon assumption (Hat-A finding the eval surfaces)

The `yarnnn-author-responsiveness.yaml` suite carries a **now-incorrect prior**, baked in three places, all citing **ADR-293 D10** which **ADR-307 withdrew 2026-05-30**:

- Suite header (L28–35): *"per ADR-293 D10, until Phase 4 … the Reviewer under bounded mode falls through to Clarify for substrate writes by canon design. A bounded-mode eval that shows 'narrate-without-attempt' is reading CANON-CONSISTENT behavior."*
- `counterfactual-autonomy-flip` prior (L82–85): *"per ADR-293 D10 pre-Phase-4, fall-through-to-Clarify is canon-consistent."*
- `counterfactual-preferences-add` prior (L131–141): *"under bounded mode pre-Phase-4, surfaces the gap via Clarify/standing_intent … rather than binding a write the system can't route."*

**This is now false.** Per FOUNDATIONS DP23 + ADR-307 (validated, HEAD `351b211`): under bounded mode a Reviewer `WriteFile` **QUEUES** as a `family='substrate'` `action_proposals` row — it does NOT fall through to Clarify, and it does NOT hard-error. The validated receipt is in the ADR header: `success=True, proposal_id=…, family='substrate', status='pending', source='reviewer:ai:reviewer-sonnet-v8'`.

**Consequence for the eval**: the responsiveness suite's bounded-mode priors must be rewritten. The new editor-coherent move under bounded mode is *"attempt the write; observe it QUEUE as a substrate proposal; narrate the queue honestly (not Clarify-deferral, not capability-denial)."* A run against the old priors would mis-read a *correct* queued write as a divergence. **This is a §1.2 cause-(d) item** (canon changed; the eval's pre-declared expectation is mis-specified) — and exactly the "behavior-correct but architecture-wrong" / "architecture-correct read mis-scored against a stale prior" failure mode the operator's ADR-307 distrust-driven arc is teaching us to catch. The eval framework's job (per the redesign §2a) is to judge against the *current mandate + current canon*, not a frozen prior.

This is a **one-suite edit** (rewrite three priors + the header caveat), landing in the same update. It is Hat-B (suite manifest), not Hat-A (no system code changes) — the *system* already shipped the correct behavior; the *eval's prior* lagged.

---

## §5 Two disciplines to promote from the ADR-307 `/tmp` script

`/tmp/validate_adr307.py` is a Hat-B one-off that encodes two disciplines the discipline doc *names* but the harness does not yet *enforce*. Both should be promoted into `run_eval_suite.py` (not left in `/tmp`):

1. **Empty-wake guard (§6.2 "empty-response caveat", S1).** The script's verdict logic treats a near-empty response as INCONCLUSIVE, never a pass, and verifies a server-side `execution_events` row exists before scoring. The discipline doc mandates this in prose; **nothing in the runner enforces it.** The runner should, per-eval, flag responses below a char threshold as `INCONCLUSIVE` in the §Read-state / §Preconditions output and require an `execution_events` receipt — so a false-empty (the twice-recurring harness trap) cannot silently render as a clean read.

2. **Architecture-shape receipt, not just behavior receipt (the transferable lesson).** The script doesn't assert "the write succeeded" — it asserts the write succeeded *in the architecturally-correct shape*: `family='substrate'` (not errored, not applied, not self-waking), with the proposal-row + execution_event + self-wake-count receipts. The eval framework should make **receipt-capture a first-class required output of every eval** (the §6.1 scaffold's receipt-pointers), and the prose-read prompt should orient the human toward shape-correctness, not just outcome-correctness. This is already half-expressed in the v2 `prior:` fields; the harness should ensure the receipts that let a human check shape are *captured in raw/* for every eval (revision_ids, proposal rows with `family`, execution_events with `wake_source`/`status`, self-wake counts).

Neither needs new infra — both are small additions to the C4 scaffold renderer + a per-eval receipt-snapshot. The `resnapshot_eval` path (L333) already captures the substrate diff; extend its capture to include the `action_proposals.family` + `execution_events.wake_source/status` rows so the shape-receipt is in `raw/`.

---

## §6 Open questions for the operator (before §3 build)

These are the genuine decision points — not things I can resolve from the spec.

1. **Schema v1 back-compat: hard break or graceful?** The four prior session folders are v1 (`expected_dimensions`, four-dimension tables). §7.4 grandfathers them as historical artifact (don't re-run). The clean move per Singular Implementation is: **delete v1 from the runner entirely** (no dual-schema branch), leave the old session folders as frozen artifact. Confirm: hard-break the runner to v2-only, or keep a v1 read-path for archive re-render? *(Recommend: hard-break. The grandfathered folders are read as markdown, never re-run; a v1 code-path is a dual-implementation the discipline forbids.)*

2. **Does the responsiveness suite still make sense post-ADR-307?** Beyond the §4 prior-rewrite: the suite's whole arc (flip autonomy → does the Reviewer track the gate) now has a *richer* correct answer (queue, don't Clarify-defer). Worth re-reading whether the four counterfactual evals still probe the right thing, or whether ADR-307 changed the situation enough that one or two should be re-authored rather than just re-prior'd.

3. **First validation run target.** §12 says "the first session under the new shape lands after the harness changes ship." Once C1–C7 land, the natural first run is `yarnnn-author-judgment.yaml` (the 6 judgment evals — clean situations, no accumulation, lowest-risk read). Confirm that's the intended first run, vs. running responsiveness first to immediately exercise the ADR-307 queue behavior end-to-end.

---

## §7 Receipts (this audit's grounding)

- `EVAL-SUITE-DISCIPLINE.md` §8 C1–C7 (the named change-list) — read in full.
- `run_eval_suite.py:46` `SUITE_SCHEMA_VERSION = 1`; L69 v2-reject; L88 `expected_dimensions` required; L620–668 dimension tables; L745 DRAFT — confirms v1.
- `eval-suites/yarnnn-author-judgment.yaml` + `yarnnn-author-responsiveness.yaml` — confirm v2 schema authored, 10 scenarios referenced.
- `scenarios/` directory listing — all 10 referenced scenarios present (verified `test -f`).
- `operator_proxy/client.py:204–239` — SSE-decode fix live; `:349` `write_substrate` via `write_revision`.
- `operator_proxy/scenarios.py:200,465` — `_execute_setup_step` + `_write_substrate_with_author` (C3 foundation).
- ADR-307 header (`docs/adr/ADR-307-…md:3`) — Implemented + validated; bounded WriteFile → `family='substrate'` QUEUE; D10/D13 withdrawn (`:67,:91`).
- FOUNDATIONS DP23 (`FOUNDATIONS.md:702`) — one gate, one queue; canon for the shape the eval must assert.

---

## §8 Build outcome (2026-05-30, same session)

All four §6 forks confirmed (recommended path each): hard-break v2-only · re-prior-only · judgment-first · build-now. Shipped:

| Change | Site | Verification |
|---|---|---|
| **C1** schema v2 | `run_eval_suite.py` `SUITE_SCHEMA_VERSION=2`, `load_suite` (read_kind required, requires/prior/accumulates/inherits accepted, expected_dimensions dropped, qualitative budget floors deleted) | both v2 suites load (judgment 6 / responsiveness 4 + 3-eval accumulating arc, inherits resolved); v1 baseline rejected |
| **C2** `check_preconditions` | `services/operator_proxy/scenarios.py` | 6 assertion shapes unit-tested offline (field-equals ±, absent ±, contains/not_contains) — all correct |
| **C3** `establish_substrate` + `_delete_substrate_file` | `services/operator_proxy/scenarios.py` | reset-to-clean default; `absent: true` delete preserves revision chain (ADR-209); accumulates:true skips reset |
| **C4** prose scaffold | `run_eval_suite.py::render_session_md` | renders §Preconditions + §The read (blank) + §What-the-session-says + §Recommendations + §Cost; **no Pass? cells, no `**DRAFT**`, no dimension table** (asserted) |
| **C5** read-state | `render_session_md` §Read-state | replaces DRAFT/POPULATED; names what was read |
| **C5b** empty-wake guard + shape receipts | `_detect_empty_responses` + `capture_shape_receipts` → `raw/{eval}/shape-receipts.md` | promoted from `/tmp/validate_adr307.py`; INCONCLUSIVE flag renders; `family`/`wake_source`/self-wake captured |
| **C6** cost windowing | `compose_cost_rollup` | confirmed `created_at`-windowed (already correct in v1) |
| **C7** README note | `README.md` boundary section | updated Proposed→built + empty-wake/shape-receipt notes |
| **§4** stale priors | `yarnnn-author-responsiveness.yaml` (header + 2 eval priors) | bounded→QUEUE-not-Clarify per ADR-307; old ADR-293 D10 framing marked superseded; suite still loads |

**Not yet done** (the load-bearing remainder): **no live session run.** The unit-level harness checks pass; the framework is proven end-to-end only by a real read. First run = `yarnnn-author-judgment.yaml` (judgment-first decision), a separate Hat-B session. EVAL-SUITE-DISCIPLINE.md §12 flipped to Implemented; this is the gate before it can claim live validation.
