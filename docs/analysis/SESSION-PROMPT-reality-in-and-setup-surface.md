# SESSION PROMPT — Reality-In Audit + ADR Drafting (Consequence Pipe · Harvest Invocation · Setup Rendering)

**Created:** 2026-06-10 (by the strategy-regroup session; operator: KVK)
**Intended executor:** a fresh Claude Code session on this repo
**Shape of work:** Hat-B audit verification → Hat-A ADR drafts (Proposed) →
**PAUSE for operator ratification** → phased implementation per repo norms.
Do NOT implement before the ADRs are ratified unless the operator says
otherwise in-session.

---

## 0. Read first (in this order)

1. `docs/analysis/reality-in-current-standing-and-setup-as-rendering-2026-06-10.md` — the discourse capture this prompt executes; its §5 lists the open design questions you must resolve or explicitly defer.
2. `docs/analysis/author-blindness-and-invariant-capabilities-2026-06-10.md` — why this work is the committed, path-invariant direction.
3. `docs/analysis/cumulative-workspace-product-formulation-2026-06-10.md` — the ratified product frame ("workspace where work is cumulative"; the moat = calibration against ground truth the agent cannot author).
4. ADRs: 153 (platform-content sunset — the purity rule), 195 v2 (OutcomeProvider/money-truth substrate), 205 (inline-action→recurrence graduation), 209 (authored substrate/attribution), 226 (activation flow + chat overlay), 244 (workspace settings surface + `first_run` redirect), 304 (operator-addressing writes), 327 (budget + calibration mirror), 282 (kernel/instance ground-truth vocabulary).
5. `CLAUDE.md` — execution disciplines (singular implementation, doc-first, render parity, test gates).

## 1. Task A — Verify the audit (receipts, ~30 min)

Re-verify the current-standing claims in the discourse capture against live
code (they were grepped 2026-06-10; concurrent lanes move fast):

- `api/services/outcomes/` — provider count (expected: Trading + Commerce only in `reconciler.DEFAULT_PROVIDERS`), `OutcomeCandidate` shape.
- `docs/programs/alpha-author/MANIFEST.yaml` — confirm NO `substrate_abi.ground_truth` declared.
- `api/services/platform_tools.py` — read-tool groups (slack/notion/github/trading/commerce), `SYSTEM_INFRASTRUCTURE_TOOLS`, `write_email` audience tools.
- `api/routes/documents.py` — upload constraints (single-file, 25MB).
- `api/services/primitives/mirror_calibration.py` + `bundle_reader.get_ground_truth_for_workspace` — the loop's read path.
- ADR-244 workspace-state shape (`substrate_status`, `capability_gaps`) and the `first_run=1` redirect in `web/app/auth/callback/`.

If any claim has drifted, correct the discourse capture's §1 table in place
(add a dated correction note) before drafting.

## 2. Task B — ADR draft #1: Consequence Pipe Generalization

Working title: **"Ground-Truth Intake — Generalizing the Consequence Pipe
Beyond Platform Providers."** Backend-leaning. Decisions the ADR must make
explicitly:

1. **Manual/operator intake provider** — a CSV/structured-import path producing
   `OutcomeCandidate` rows through the existing reconciler + ledger
   (idempotency keys, optional `proposal_id` linking). One pipe; no parallel
   ingestion path.
2. **Attestation level on every outcome row** — `platform | operator | agent`
   per the discourse capture §2. Decide: label-only at first, or
   calibration-weighting (lean label-first; weighting is a follow-on when
   evidence demands). The moat claim "ground truth the agent cannot author"
   must remain honest — name how each level preserves or qualifies it.
3. **Retrospective mode** — the same intake pointed at the past (historical
   decisions + outcomes, pre-YARNNN). This is the cold-start/calibration-
   backfill answer (ADR-320 seam). Decide how historical rows are
   distinguished (e.g., `executed_at` in the past + a `retrospective` flag)
   and whether they enter `_calibration.md` weighted/segmented.
4. **alpha-author ground truth** — declare `substrate_abi.ground_truth` for the
   bundle (multi-signal per its MANIFEST oracle shape) + the accumulation
   recurrence that writes it, so the second active program's loop lights up.
   Bundle-side work; extend `api/test_adr287_bundle_conformance.py` in the
   same commit per ADR-287 discipline.
5. **Naming** — "OutcomeProvider" misled the operator (read as pipeline-OUT).
   Decide whether to rename at the module/vocabulary level (candidates:
   ground-truth intake, consequence pipe — Axiom 8 vocabulary per ADR-282) or
   keep the class name and fix the canon vocabulary only. Singular
   implementation either way — no alias layers.

**Explicitly out of scope / anti-goals (state them in the ADR):** no
continuous sync revival (ADR-153 stands); no per-vertical API connectors yet
(CSV/manual is the universal fallback; connectors are bundle-side follow-ons);
no coverage/freshness tracking state (the substrate is the record).

## 3. Task C — ADR draft #2: Harvest as Inline Invocation + Setup as Rendering

Working title: **"Setup-as-Rendering — the /setup Sequence View and the
Harvest Invocation."** Frontend-leaning with light backend. Decisions:

1. **`/setup` is a RENDERING, not a system.** A full-bleed, ordered,
   re-enterable sequence view over the **existing** workspace-state endpoint
   (ADR-244 shape). One state source, one action set (activate program ·
   connect platform · author via ADR-226 chat overlay deep-link · fire harvest
   invocation), two renderings (sequence = `/setup`; reference = Settings →
   Workspace, unchanged). **Hard rule: no stored wizard-state.** Progress is
   derived from substrate (files authored? connections active? harvest
   invocations ran?). If a step needs state the substrate can't derive, the
   step is wrong.
2. **First-run flow** — `auth/callback` redirects first-run operators to
   `/setup` instead of `/settings?tab=workspace&first_run=1` (amends ADR-244
   D5). Settings keeps everything it has; `/setup` is re-enterable any time
   (the "Migration Assistant is not only for first boot" property).
3. **The harvest invocation** — an ordinary addressed inline action (ADR-205):
   reads via existing Mode-A read tools (slack/notion/github reads, uploads,
   web), writes attributed substrate (`authored_by="agent:harvest"` or
   per-taxonomy equivalent — verify against `authored_substrate.is_valid_author`)
   into context domains, narrative entries as its only trace. **No harvest
   subsystem, no coverage state** (the dual-tracking retraction in the
   discourse capture §3 is binding).
4. **Scope control** — operator picks sources/ranges, sees a dry-run estimate
   ("~N pages → these domains"), then fires. Decide the minimal UX (this can
   be chat-mediated rather than custom UI in v1 — weigh both, pick one).
5. **Bulk upload** — decide whether multi-file/archive upload lands in this
   ADR or is deferred (current: single-file 25MB). Lean: include the minimal
   multi-file path here since Mode-B is half of "bring in reality."
6. **Home/Files boundaries** — restate (don't reimplement): Home's empty state
   POINTS to `/setup` (ADR-312 constitution band CTA), never grows setup
   functionality; Files stays the raw substrate surface (ADR-329).

## 4. Discipline guardrails (binding)

- **Hats:** Task A is Hat-B; Tasks B/C ADRs are Hat-A canon. Substrate-receipts
  under every load-bearing claim.
- **Singular implementation:** one intake pipe, one workspace-state source, two
  renderings max. Delete/supersede anything the ADRs replace — no compat shims.
- **The dimensional test before any new mechanic:** is this a new cell or an
  existing mechanism with a different trigger shape? (Harvest already failed
  the "new mechanic" test — it's an invocation.)
- **The substrate-is-the-record test for any state addition:** derivation over
  substrate = fine; stored setup/coverage/progress state = reject.
- **ADR conventions:** status Proposed; supersede/amend banners on touched ADRs
  (244 D5, 226 cross-ref, 195 extension); FOUNDATIONS/GLOSSARY touches only if
  vocabulary changes (Task B decision 5); regression-gate test files per repo
  norm; `api/prompts/CHANGELOG.md` if any LLM-facing prompt changes.
- **Render parity:** Task B touches scheduler-adjacent code paths
  (reconciler) — check all 4 Render services' env/deploy implications.
- **Pause point:** present both ADR drafts + decision tables to the operator
  before implementation. The operator ratifies; phases land per ADR.

## 5. Explicitly out of scope for this session

ICP lock / GTM (separate track — see GTM_POSITIONING v4 §7) · pricing ADR ·
publish/social last-mile · per-vertical connectors · bundle #3 · the
bare-kernel "default program" question (carried open in the discourse capture
§5.5 — note it in the ADR's open-questions section, don't resolve it).
