# Evaluation Infrastructure Audit + Consolidation — Pre-Sprint Foundation

**Captured**: 2026-05-27. Hat-B analysis memo with same-commit Hat-A consolidation refactor (cross-hat shape per `docs/evaluations/README.md` discipline rule 6 — small, additive, named in-canon precedent).

**Origin**: operator asked whether sprint-method design should be preceded by foundation work. Audit surfaced real structural drift in the evaluation infrastructure itself. Refactor lands same-commit because the consolidation is small + additive + has clean in-canon precedent.

**Companion artifacts**:
- [`docs/evaluations/2026-05-27-000919-mandate-coherence-criterion/findings.md`](../evaluations/2026-05-27-000919-mandate-coherence-criterion/) — the second criterion the sprint method needs to measure against
- [`docs/analysis/alpha-trader-playbook-audit-2026-05-27.md`](alpha-trader-playbook-audit-2026-05-27.md) — playbook-side audit; this memo is the infrastructure-side audit

---

## §1 The dual-path drift

The operator-proxy harness (`api/services/operator_proxy/` + `api/scripts/operator/`) shipped along two paths that grew independently without an explicit boundary between them.

**Path A — Declarative YAML scenarios** (`api/scripts/operator/run_scenario.py` + `api/services/operator_proxy/scenarios.py` + `docs/evaluations/scenarios/*.yaml`):

- 3 trader-shape YAML files (`warm-start-auto-execute`, `cold-start-governance-self-amend`, `post-refusal-self-amendment-probe`)
- Documented schema v1 at `docs/evaluations/README.md` §"Scenario schema (v1)"
- 4 turn shapes pre-refactor: `send_message`, `emit_proposal`, `approve_proposal`, `reject_proposal`
- 2 setup shapes pre-refactor: `fire`, `write_substrate`
- All scenarios trader-targeted (kvk + alpha-trader persona)

**Path B — Imperative Python canary scripts** (`api/scripts/operator/canary_phase4_*.py`):

- 5 scripts: `canary_phase4_v1` through `v5` (plus `canary_v4_substrate_event` + `canary_phase4_operator_email` = 7 total imperative scripts)
- All target `yarnnn-author` persona
- Each script is its own standalone Python file calling `OperatorProxy` directly
- Total LOC: 1,140 across the 7 scripts; substantial duplication (see §2)

**Why the drift happened** (structurally, not as fault):

- The YAML schema's only mid-scenario substrate-mutation path was via setup-block `write_substrate`. Author-shape probes need *mid-scenario* substrate writes — seed a draft, then flip status to fire the reactive hook, then wait for Reviewer wake. The YAML schema couldn't express this; pure-Python was the only path.
- `emit_proposal` is the only proposal-shaped turn; author-shape probes don't emit proposals (the canonical Reviewer wake trigger for authors is the substrate-event hook on `status: ready_for_review`, not `ProposeAction`).
- The 5 canary scripts grew through an iterative empirical investigation (ADR-299 Discoveries 3 + 4), where each variant tested one isolated variable. Pure-Python flexibility was the right tool for the investigation; the duplication accumulated as a side-effect.

**Note**: a README claim that `emit_proposal` is "stubbed" (per README §"Turn shapes" pre-this-refactor) is stale — `services/operator_proxy/scenarios.py::_emit_proposal_from_template` has a real implementation calling `handle_propose_action` via `proposal_templates.TEMPLATES`. README updated this commit.

---

## §2 Boilerplate duplication inventory

Across the 5 `canary_phase4_*` scripts (excluding `canary_v4_substrate_event` + `canary_phase4_operator_email` which have different shapes), the following code is duplicated verbatim or near-verbatim in each script:

**(a) Path-convention constants** — duplicated in 4/5 canary scripts:
```python
FRESH_PIECE_SLUG = "phase4-canary-vN-..."
FRESH_PIECE_DIR = f"/workspace/context/authored/{FRESH_PIECE_SLUG}"
PROFILE_PATH = f"{FRESH_PIECE_DIR}/profile.md"
CONTENT_PATH = f"{FRESH_PIECE_DIR}/content.md"
```

**(b) Frontmatter status-flip regex** — duplicated verbatim in 4/5 canary scripts:
```python
def _flip_status(content: str, new_value: str) -> str:
    pattern = re.compile(r"^status:\s*\S+", re.MULTILINE)
    if not pattern.search(content):
        raise ValueError("No `status:` line found in profile.md frontmatter")
    return pattern.sub(f"status: {new_value}", content, count=1)

def _extract_status(content: str) -> str | None:
    m = re.search(r"^status:\s*(\S+)", content, flags=re.MULTILINE)
    return m.group(1) if m else None
```

**(c) sys.path bootstrap + import** — duplicated verbatim in 5/5 canary scripts:
```python
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from services.operator_proxy.client import OperatorProxy  # noqa: E402
```

**(d) Receipt-print formatting** — duplicated near-verbatim in 5/5 canary scripts:
```python
print(f"=== Canary {label} fired ===")
print(f"Expected Reviewer wake within ~1-5 min of {now3}.")
print(f"Watch:")
print(f"  wake_queue WHERE dedup_key = '{write3['revision_id']}'")
print(f"  execution_events WHERE wake_source='substrate_event' AND created_at > '{now3}'")
print(f"  reviewer substrate writes (judgment_log.md + standing_intent.md)")
```

**(e) Draft profile + content shapes** — the `PROFILE_DRAFT` template + content variants are sometimes shared verbatim across canary versions (e.g., v3/v4/v5 share identical `CONTENT_DRAFT` because the test variable was REVIEWER_PRIMITIVES surface size, not content). The anti-pattern voice prose with list-of-three openers and "absolutely pivotal" intensifiers appears in 3 separate files.

Net: ~80 LOC of true boilerplate per script × 5 scripts = ~400 LOC of duplication.

---

## §3 Vocabulary asymmetries (cosmetic, low-priority)

Three places where the same `OperatorProxy` is documented with different command names:

- `api/scripts/operator/loop.py` REPL commands: `/feed`, `/proposals`, `/approve`, `/reject`, `/read`, `/recurrences`, `/capture`
- YAML scenario schema turn shapes (pre-refactor): `send_message`, `emit_proposal`, `approve_proposal`, `reject_proposal` (4 verbs; loop has 8)
- Canary scripts use method calls directly: `proxy.write_substrate`, `proxy.read_file`, `proxy.send_message` (no command-vocabulary layer)

The asymmetry isn't load-bearing — each surface chose verbs that fit its interaction model (REPL = short slash-commands; YAML = clear verb prefixes; Python = method names). Mentioned here for completeness, not for normalization. No refactor proposed.

---

## §4 Decision: consolidate without retiring either path

**Decision**: extend the YAML schema to cover the author-shape probe pattern + extract the canary boilerplate into a shared helpers module + add a draft-templates registry mirroring the proposal-templates registry. **Preserve all 5 existing canary scripts as historical-trace substrate-receipts** of the ADR-299 investigation arc; do not migrate them.

**Why this is the right consolidation**:

1. **Closes the dual-path drift at the authoring surface.** Going forward, new author-shape probes should be YAML scenarios. The capability the YAML schema lacked (mid-scenario substrate write + status-flip convenience) is now present. The canonical authoring path is YAML; pure-Python remains available for the rare probe whose investigation shape needs Python flexibility.

2. **Doesn't break or migrate working substrate-receipts.** The 5 existing canary scripts are part of the ADR-299 substrate-receipts (each ran live against production, produced wake_queue rows + execution_events + revision chains). Migrating them retroactively would dissolve the receipts. Preserving them as historical-trace artifacts honors the ADR-209 attribution discipline (every revision in the chain stays attributable to its actual authoring event).

3. **Lowest-friction extension path forward.** Future canaries that genuinely need Python flexibility can import `_canary_helpers.py` for the shared boilerplate. New canaries' LOC drops from ~150 lines to ~50 lines because path conventions + status-flip + receipt-print are imported.

4. **Named in-canon precedent.** `services/operator_proxy/proposal_templates.py` is exactly the pattern this refactor's `draft_templates.py` follows — named templates in a registry, `get_template(name)` resolver, defensive copy on get. Zero novel architectural surface introduced; the discipline is "extend the same pattern, don't invent a new one."

5. **Cross-hat single commit fit per discipline rule 6.** The refactor is additive (no deletions of existing scenarios or canary scripts), small (~190 LOC across 4 files), and has named in-canon precedent. Multi-commit ceremony would add overhead without producing additional clarity.

**Alternatives considered and rejected**:

- **Migrate the 5 canary scripts to YAML scenarios + delete the Python versions.** Rejected: destroys substrate-receipts of the ADR-299 arc.
- **Keep YAML schema as-is + write new author-shape canaries as Python scripts.** Rejected: perpetuates the dual-path drift; new probe authoring stays expensive (~150 LOC per probe) and harder to read across the active set.
- **Build a sprint-runner layer that orchestrates both YAML scenarios AND Python canaries.** Rejected: cements dual-path into the sprint layer; the right move is to unify at the unit-of-probing level first.

---

## §5 What this commit lands

**Three additive files**:

1. **`api/scripts/operator/_canary_helpers.py`** (~95 LOC). Extracts the path-convention helpers (`piece_paths(slug)`), frontmatter mutations (`flip_status`, `extract_status`), and receipt-print formatting (`print_canary_receipt`) into a shared module. Existing canary scripts NOT modified; new canaries import this module.

2. **`api/services/operator_proxy/draft_templates.py`** (~130 LOC). Mirrors `proposal_templates.py` pattern. Two initial templates: `anti-pattern-voice` (Reviewer should defer with directive) and `clean-voice` (Reviewer should approve). Provides the contrast pair for evaluating verdict-tracks-content-quality. Registry pattern: `TEMPLATES` dict + `get_template(name)` resolver + `KeyError` on unknown name + defensive copy on get.

3. **`docs/analysis/evaluation-infrastructure-audit-2026-05-27.md`** (this file). Hat-B audit memo with same-commit Hat-A consolidation rationale per discipline rule 6.

**Three additive extensions to existing files**:

4. **`api/services/operator_proxy/scenarios.py`** — added 3 new turn-shape handlers (`write_substrate` as turn, `flip_frontmatter_field`, plus `seed_draft` in setup-block), 2 new helpers (`_seed_draft_from_template`, `_replace_yaml_frontmatter_field`), updated module docstring to document the new shapes. ~95 LOC added; no existing handlers modified.

5. **`docs/evaluations/README.md`** §"Scenario schema (v1)" + "Turn shapes" tables — added 3 new entries documenting the new turn/setup shapes; updated stale "stubbed" note on `emit_proposal`; added schema-lineage paragraph documenting when the new shapes landed and the singular-implementation discipline that motivated the consolidation.

**Smoke test passed (pre-commit verification)**:
- All 3 existing YAML scenarios re-parse cleanly via `Scenario.from_file(...)` — same setup/turn counts as before
- `_replace_yaml_frontmatter_field` handles happy path + missing-field error path
- `draft_templates.get_template('anti-pattern-voice')` returns expected shape
- `_canary_helpers.piece_paths(...)` + `flip_status` + `extract_status` work end-to-end

**What this commit explicitly does NOT do**:
- Does not delete any of the 5 existing canary scripts
- Does not migrate any of the 3 existing YAML scenarios (no behavior change for them)
- Does not introduce sprint-runner orchestration (that's the next layer, gated on this consolidation)
- Does not modify `OperatorProxy` client or `CaptureSession` (primitive layer is fine as-is)
- Does not introduce ADR — the audit + consolidation decision is developer-surface scaffolding per two-hats rule, not YARNNN system canon that real operators inherit

---

## §6 What this unblocks

Sprint-method design (the operator's actual question) now proceeds on stable foundations:

- **Author-shape probes are now first-class YAML scenarios.** A sprint manifest can reference 5-8 YAML scenarios as the unit of probing, each authorable in 1 screen of YAML instead of 150 lines of Python.
- **Draft-template reuse is now mechanical.** A sprint that probes Reviewer behavior on N variants of voice-quality content just lists N+1 scenarios (1 clean-voice baseline + N anti-pattern variants), all drawing from `draft_templates.TEMPLATES`.
- **Canary helper extraction means future canaries are cheap.** If a sprint scenario needs pure-Python flexibility (rare), the helper imports drop the per-probe authoring cost materially.

What still needs design work after this commit (out of scope here):

- **Sprint manifest schema** (`sprint.yaml`?): how to declare a sequence of scenarios with shared substrate accumulation between them
- **Sprint summary rollup template**: how to aggregate per-scenario findings into a single sprint-summary findings.md
- **Per-cell mandate-coherence tagging template**: how to make the §3.1 Axis-A SQL + Axis-B human-read manageable across n=~30 wakes per sprint
- **Session-start guide for sprint discipline**: `docs/evaluations/sessions/alpha-author-sprint.md` analog to the existing operator-absent observation guide, codifying the opposite discipline (active engagement, scripted probes, accelerated cadence)

These belong in a follow-up Hat-B + Hat-A cycle once the operator confirms the sprint shape (see operator's pending question on Shape 1/2/3 from the conversation that triggered this audit).

---

## §7 What this audit does NOT do

1. **Does not retire either evaluation path.** Both YAML scenarios and Python canaries remain available; the consolidation establishes which is canonical going forward without invalidating historical artifacts.

2. **Does not propose a new ADR.** Evaluation infrastructure is developer-surface scaffolding (per `docs/evaluations/README.md` §"The Hat We Wear in This Directory"); it lives outside YARNNN canon real operators inherit. No ADR drafted.

3. **Does not modify any real workspace's substrate.** All changes are to source files + the README. Zero impact on `kvkthecreator@gmail.com` or `yarnnn-author@yarnnn.com` substrate.

4. **Does not address the vocabulary asymmetries (§3).** Mentioned for completeness but not refactored — each surface chose verbs that fit its interaction model.

---

## §8 Cross-references

- Companion playbook audit: [`docs/analysis/alpha-trader-playbook-audit-2026-05-27.md`](alpha-trader-playbook-audit-2026-05-27.md)
- Companion criterion: [`docs/evaluations/2026-05-27-000919-mandate-coherence-criterion/findings.md`](../evaluations/2026-05-27-000919-mandate-coherence-criterion/)
- Evaluation discipline canon: [`docs/evaluations/README.md`](../evaluations/README.md)
- Operator-proxy canon: ADR-294 (operator-proxy capability)
- The ADR-299 investigation arc the 5 canary scripts captured: `docs/evaluations/2026-05-24-054214-adr299-phase4-canary-red/`, `docs/evaluations/2026-05-25-042346-adr299-always-surface-resolution/`, `docs/evaluations/2026-05-25-053951-reviewer-behavior-population-audit/`
- Singular-implementation discipline source: CLAUDE.md §"Core Execution Disciplines" rule 2

---

## §9 Status

**Implemented** in commit landing this memo. Refactor is additive + smoke-tested; no follow-on work required to close this audit.

Next step (operator-gated): sprint-method design layered on this foundation.

## Last updated

2026-05-27 — initial audit + same-commit consolidation refactor per discipline rule 6.
