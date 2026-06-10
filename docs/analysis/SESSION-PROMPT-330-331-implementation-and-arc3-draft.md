# SESSION PROMPT — Implement ADR-330 + ADR-331, then Draft Arc-3 (Perception Field)

**Created:** 2026-06-10 (by the strategy-regroup session; operator: KVK)
**Intended executor:** a fresh Claude Code session on this repo
**Shape of work:** three stages with different gates —
- **Stage A (ADR-330 implementation)** — ratified, proceed WITHOUT pauses, phase-per-commit.
- **Stage B (ADR-331 implementation)** — ratified, proceed WITHOUT pauses, phase-per-commit.
- **Stage C (arc-3 ADR draft)** — draft ONLY; **HARD PAUSE for operator ratification. No arc-3 code.**
Program-assembly (route i) is explicitly OUT of this session (named future ADR per ADR-332 §5 ledger).

---

## 0. Read first (in this order)

1. `docs/adr/ADR-330-ground-truth-intake.md` + `docs/adr/ADR-331-setup-as-rendering.md` — both **Ratified** (commit `e444939` records ratification + streamline edits; status headers say Proposed-for-ratification — flip them as phases land per repo norms).
2. `docs/adr/ADR-332-four-flow-completeness-model.md` — the canonical frame (FOUNDATIONS v9.1 DP26). Note its §5 follow-up ledger — several rows are YOURS this session (ADR-330 P5 vocabulary; WORKSPACE docs at 331; arc-3 items).
3. `docs/analysis/perception-under-calibration-arc3-foundation-2026-06-10.md` — arc-3's frozen foundation, **including §8** (MCP feasibility evidence + route-i hardening + the dependency ordering).
4. `docs/analysis/four-flow-completeness-and-program-floor-2026-06-10.md` + `docs/analysis/reality-in-current-standing-and-setup-as-rendering-2026-06-10.md` (with its §0 drift corrections — `operation/` paths per ADR-320, `/program` redirect per ADR-297, atomic surfaces).
5. `CLAUDE.md` execution disciplines. Concurrent lanes are active — **stage by name only, never `git add -A`**. Re-verify every code receipt before relying on it; main moves hourly.

## 1. Stage A — ADR-330 implementation (Phases 1–5, ratified, no pauses)

Per the ADR's §10 plan. Summary of phases (the ADR is authoritative; this is the checklist):

1. **P1** — `attestation: Literal["platform","operator","agent"]` + `retrospective: bool` on `OutcomeCandidate`; platform providers stamp `platform`; `fold_outcome_candidates` writes fields + segments retrospective rows in the ground-truth file; mirror surfaces both. Backward-compatible defaults.
2. **P2** — `OperatorOutcomeProvider` (CSV/manual import via staged upload), addressed-invocation entrypoint, idempotency through the existing ledger dedup. NOT added to `DEFAULT_PROVIDERS`.
3. **P3** — retrospective mode end-to-end (flag honored; mirror presents segments labeled).
4. **P4** — alpha-author `substrate_abi.ground_truth: operation/authored/_signal.md` declaration + extend `api/test_adr287_bundle_conformance.py` same commit. **This is the proof** — the second active program's loop lights up.
5. **P5** — vocabulary: FOUNDATIONS Axiom 8 + GLOSSARY gain "ground-truth intake" + "consequence pipe" (the GLOSSARY Four-Flows section has a *Reserved* row waiting for you — fill it, don't duplicate); docstring rewording in `outcomes/*.py` incl. the stale `action_outcomes` prose fix. Class names STAY (D5).

New regression gate `api/test_adr330_ground_truth_intake.py` per the ADR. Render parity per ADR §9 (reconciler runs on API + Scheduler; confirm `DEFAULT_PROVIDERS` daily run unchanged).

## 2. Stage B — ADR-331 implementation (Phases 1–3, ratified, no pauses)

Per the ADR's §10 plan:

1. **P1** — `setup` in `KERNEL_SURFACES` (`archetype="sequence"`, `register="os-config"`, `substrate_paths: []`); Sequence-archetype renderer over `api.workspace.getState()`; first-run redirect `auth/callback` → `/setup?first_run=1`; Home `UnactivatedHomeCTA` repointed; summon-index via compositor confirmed. Sequence archetype added to ADR-198 catalog same commit. **Hard rule: no stored wizard-state — every step status derived from substrate.**
2. **P2** — harvest invocation (`agent:harvest` attribution — verify against `is_valid_author`; addressed inline action, existing read tools + WriteFile, narrative-only trace, NO coverage state of any kind) + metadata-only dry-run endpoint + the scope picker UI (ephemeral selection, dry-run estimate, confirm-to-fire). `api/prompts/CHANGELOG.md` entry for the harvest prompt.
3. **P3** — multi-file + `.zip` upload through the existing single-file path (25MB per file, per-file error reporting, archive as transport envelope only).

New regression gate `api/test_adr331_setup_rendering.py` per the ADR. Doc cascade per ADR-332 §5: update `docs/architecture/WORKSPACE.md` + `docs/design/WORKSPACE.md` with the `/setup` + flow-declaration framing in Stage B's final commit.

## 3. Stage C — Arc-3 ADR draft (DRAFT ONLY — hard pause before any code)

Draft **ADR-333 (or next free number) — The Perception Field: Watch Declarations, Observation Contract, MCP-Client Transport.** Authoritative foundation: the perception doc (§1–§8) + ADR-332 D5. The draft must decide (as proposals for ratification):

1. **Watch declaration** — kernel substrate convention (the `_universe.yaml` pattern promoted; where it lives under ADR-320's five roots — likely `operation/` or `constitution/`-adjacent; resolve with the topology's diagnostic test), program-declared per ADR-332 D3 (no freehand workspace path).
2. **Observation contract** — the perception twin of `OutcomeCandidate`: attributed, attested (REUSE the ADR-330 enum — verify the implemented shape from Stage A, don't re-derive), source-referenced, dated, distilled. Distill-don't-mirror binding (ADR-153).
3. **MCP client (crawl stage)** — one kernel client; bindings on the `platform_connections` pattern (encrypted, OAuth 2.1 + `.well-known` discovery per the June-2025 spec; note the 2026-07-28 stateless-core RC — build against the stable surface, flag RC churn); foreign tools as dynamic capability-gated dispatch entries; attestation graded by server provenance; injection containment = distill-only + Reviewer-gated actions + budget metering. Registry-search (walk stage) SPECCED but explicitly deferred within the ADR.
4. **Flow-completeness conformance gate** — the general four-flow assertion in `api/test_adr287_bundle_conformance.py` (every active program declares all four flows or marks N/A with rationale) per ADR-332 D4. Include the `docs/programs/README.md` bundle-authoring guidance row from ADR-332 §5.
5. **Calibrated attention** — how `by_signal`-style attribution generalizes so flow 4 judges watches; label-first (no weighting), same posture as ADR-330 D2.
6. **Canon cascade plan** — FOUNDATIONS axiom-text for the four clauses (*attributed observation · declared watches · transports-as-peripherals · calibrated attention*), GLOSSARY full entries (observation, watch, perception field), SERVICE-MODEL framing pass — listed in the draft, landed only at ratification.

**Anti-goals to state in the draft:** no perception manager / source-freshness state (substrate is the record); no connector catalog (one client, ecosystem servers); no webhook/push ingestion v1 (pull + existing wake sources); registry-resolution UX deferred to walk; program-assembly (route i) explicitly out — it is the *next* ADR after this one ratifies (ADR-332 §5 ledger row).

**Then STOP.** Present the draft + decision table to the operator. No arc-3 code, no canon cascade, no status flip.

## 4. Binding disciplines (all stages)

Substrate-is-the-record test on every state addition · dimensional test on every "new" mechanic · singular implementation (no shims, no aliases, no parallel paths) · stage-by-name commits · phase-per-commit, each landing green · status flips per repo norms as phases complete · `api/prompts/CHANGELOG.md` for any LLM-facing prompt change · Render-parity check where ADRs flag it · Hat A for implementation + ADR text, receipts under every claim.

## 5. Out of scope (this session)

Program-assembly ADR (route i) · registry-search implementation (walk) · ICP/GTM/pricing/layman-noun (strategy lane) · publish last-mile · drive/cloud-storage connectors · any perception code before arc-3 ratification.
