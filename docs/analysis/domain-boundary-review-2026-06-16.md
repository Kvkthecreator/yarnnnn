# Domain-Boundary Review — Step 1 of the Re-Evaluation Pass

**Status:** Hat B (evaluation finding) — records observed boundary state with substrate receipts; recommends, does not amend code/ADRs.
**Date:** 2026-06-16
**Hat:** B
**Authors:** KVK (operator), Claude (collaborator)
**Scope:** Executes §7.3 of [`yarnnn-product-feature-scope-and-standing-2026-06-15.md`](yarnnn-product-feature-scope-and-standing-2026-06-15.md) (the benchmark). Audits the eleven concern-domains (benchmark §2) for code-level *blur* — two domains bleeding into one — prioritizing the two suspect seams the benchmark named: **D3 perception ↔ D4 execution** (the watch→recurrence seam) and **D6 calibration ↔ D7 seat** (the cross-class calibration write).
**Method:** three parallel read-only `Explore` sweeps over `api/`, each required to return `file:line` receipts and a CLEAN / BLURRED / PARTIAL verdict. No code edited.

---

## Verdict summary

| Seam audited | Domains | Verdict | Headline |
|---|---|---|---|
| Watch → recurrence | D3 ↔ D4 | ✅ **CLEAN** | coupling is only the recurrence-slug pointer + the distilled-observation write |
| Calibration write | D6 ↔ D7 | ✅ **CLEAN** | calibration is system-written, seat-read; zero cross-class write in live code |
| Governance lock-gate + ownership | D8, D1, D2, D9 | ✅ **CLEAN** | one unified `_is_path_locked`; five-root migration complete; single write path |

**No boundary blur found.** All three seams are clean. The review nonetheless surfaced **three findings** — two benchmark/canon corrections and one canon-vs-code drift — because the audit verified *actual* code state against *documented* state.

---

## Seam 1 — D3 Perception ↔ D4 Execution: CLEAN

The two domains communicate through exactly two channels and nothing more:
1. the **recurrence-slug pointer** (a watch's `recurrence` field names the recurrence the scheduler fires), and
2. the **distilled-observation write** (the mechanical primitive writes to the watch's `distills_to` path; execution never reads it).

Receipts:
- `bundle_reader.py:378-405` — `get_watches_for_workspace()` reads `substrate_abi.watches`; called only from `routes/sources.py` (dashboard), **never** from the scheduler/dispatcher.
- `wake.py:977-1199` — `_dispatch_mechanical()` parses `@primitive: <Name>(...)` and looks up a handler by name; zero knowledge of tickers/universe/regime/observation shape.
- `scheduling.py:280-368` — `compute_next_run_at()` is pure timing math over a `Recurrence`; no watch fields.
- `primitives/track_web_sources.py:76-162,282-318` — the mechanical watch-read writes distilled signal with `authored_by="system:track-web-sources"`; no scheduling knowledge.
- `primitives/registry.py:559-564` — perception primitives are dispatcher-only (`HANDLERS`), not in CHAT/HEADLESS/REVIEWER surfaces.

No dual "read on cadence" path. The only cross-reference is a read-only dashboard accessor (`routes/sources.py:207-210`), which is neither D3 nor D4. **Boundary clean by design.**

## Seam 2 — D6 Calibration ↔ D7 Seat: CLEAN (with a drift finding, F2)

The live calibration trail is **system-written and seat-read**, with no cross-class write:
- **Written:** `primitives/mirror_calibration.py:127,357-371` → `system/_calibration.md`, `authored_by="system:mirror-calibration"` (deterministic, no judgment).
- **Read:** `reviewer_envelope.py:116` pre-loads `SYSTEM_CALIBRATION_PATH` into the wake envelope. The seat reads calibration; it never writes it.
- **Reconciler** (`outcomes/ledger.py:254,307,941`) writes only `operation/{domain}/_money_truth.md` + `operation/_money_truth_summary.md` (`authored_by="system:outcome-reconciliation"`). It imports only outcome providers — never `reviewer_agent` / `occupant_contract` / persona logic.
- `by_signal` expectancy is computed once (`ledger.py:540-547`); the seat reads it, never recomputes.

The boundary is **clean and, in the live implementation, even cleaner than ADR-320 D6 designed** (no cross-class write exists at all — see F2).

## Seam 3 — D8 Governance lock-gate + ownership: CLEAN (with a standing correction, F1)

- **Unified gate:** one `_is_path_locked(caller_class, path)` (`primitives/workspace.py:1774`) + one `CALLER_WRITE_POLICY` prefix table (`workspace_paths.py:204-211`); the legacy `_is_path_locked_for_reviewer` + `_is_path_locked_for_mcp` pair is deleted, gated by `test_adr320_permission_topology.py`.
- **Five-root migration complete:** all path constants use `governance/ constitution/ persona/ operation/ system/`; legacy `context/_shared/ review/ memory/` gone. `conventions.py:286-289` no longer redefines path constants (singular source).
- **Single write path:** every content mutation routes through `authored_substrate.py::write_revision`; the only direct `workspace_files` write is the permitted ADR-209 metadata-only embedding update (`primitives/workspace.py:46`).
- **D9 vs D7:** `orchestration.py` is registry-only (no judgment logic); judgment lives wholly in `reviewer_agent.py`. Clean orchestration-vs-judgment split (ADR-216 holds).

---

## Findings

### F1 — Benchmark standing correction: D8 five-root topology is COMPLETE (◑ → ✅)
The benchmark marked the five-root topology "◑ P2–P5 in progress," sourced from the **ADR-320 status banner** ("P1 canon done; P2–P5 in progress"). The **code shows P2–P5 complete**: unified gate, migrated constants, passing `test_adr320_permission_topology.py`. 
**Action:** benchmark D8/Floor standing corrected to ✅ (this commit). **Recommend (Hat A):** flip the ADR-320 status banner to Implemented — *stale-ADR-status-vs-code gap*.

### F2 — Canon-vs-code drift: two calibration substrates, one live (Hat A — recommend, do not fix here)
Two calibration files exist with overlapping "calibration" naming:
- **`persona/calibration.md`** (`PERSONA_CALIBRATION_PATH`, `workspace_paths.py:121`) — ADR-320 D6's designed "one cross-class system-write into `persona/`." It is *declared* in the workspace guide (`orchestration.py:894` — "per-occupant judgment-vs-outcome rolling windows"), *seeded* at signup (`workspace_init.py:227`, "auto-generated by back-office task"), and referenced in `substrate_reapply.py:419,453` — **but has no live runtime writer** (no `write_revision` targets it; the back-office task implied by the seed comment is absent).
- **`system/_calibration.md`** (`SYSTEM_CALIBRATION_PATH`, `workspace_paths.py:165`) — ADR-327 D6's calibration evidence; **live** (written by `mirror_calibration.py`, read by `reviewer_envelope.py`).

The live self-improving-loop trail is `system/_calibration.md`. ADR-327's `system/`-rooted design effectively **superseded** ADR-320 D6's `persona/calibration.md` cross-class write — and is strictly cleaner (pure `system/` root, *no cross-class write exception needed*). The residue of the un-implemented design remains in five places: the `PERSONA_CALIBRATION_PATH` constant, the signup seed, the `_workspace_guide.md` entry (`orchestration.py:894`), the stale comment at `primitives/workspace.py:1787-1790` ("reconciliation writes persona/calibration.md" — it does not), and ADR-320 D6's text + the prior benchmark's "persona/calibration.md (the one system-write into the seat)" claim.
**Recommend (operator decides, Hat A):**
- (a) **Ratify the cleaner `system/_calibration.md` as the singular calibration trail** and retire `persona/calibration.md` (delete the constant, the seed, the guide entry, the ADR-320 D6 cross-class exception, the stale comment) — singular-implementation discipline; OR
- (b) if `persona/calibration.md` is meant to be a *distinct per-occupant* trail (vs `system/_calibration.md`'s cadence/attention evidence), it is **flow-incomplete** — build its writer.
Default lean: (a). The seam is clean either way; this is dead-substrate hygiene + an ADR-320/ADR-327 reconciliation, not a boundary violation.

### F3 — Minor: governance budget constant naming (verify in Step 2)
The governance budget constant reads `GOVERNANCE_BUDGET_PATH = "governance/_budget.yaml"` (sweep C), while canon prose (CLAUDE.md, ADR-320 tree) references `_token_budget.yaml`. Likely a benign rename; **flag for Step 2** to confirm one canonical name and update whichever side is stale.

---

## Benchmark corrections applied (this commit)
- D8 (Governance) and the Floor "Five-root topology" row: standing **◑ → ✅** (F1).
- D6 substrate-root cells (§2, §4): the live calibration trail is **`system/_calibration.md`**, not `persona/calibration.md`; the latter flagged per F2.
- Benchmark §7.3 marked **done**, pointing here.

## What this unblocks
- **Domain-boundary review (§7.3): COMPLETE — no blur.** The eleven-domain separation holds in code.
- **Step 2 (live-code standing verification)** can proceed with one boundary risk retired. Step 2 should resolve F2 (calibration substrate reconciliation) and F3 (budget constant name), and convert the remaining ◑/▷ standings to verified.
- **Two Hat-A items queued** (not done here): ADR-320 status-banner flip (F1); calibration-substrate reconciliation + stale-comment fix (F2).
