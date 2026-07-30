# Eval-layer audit 2026-07-31 — zero of nine suites could fire; the layer gets its gates

**Status**: CLOSED — layer repaired to a runnable floor; two mechanical gates landed
**Hat**: B (the layer IS the developer toolchain); the two gate tests are the CI artifacts
**Trigger**: operator hypothesis that the eval suites had drifted against the code, plus the
prompt-ablation principles (docs/analysis/prompt-engineering-principles-2026-07-30.md):
every asset guilty until it proves value; verify before finishing; a probe nothing
exercises rots green — receipted twice in the 2026-07-30 envelope audit.

## 1. Headline findings

**Probes**: 9 of 39 probe scripts carried `Recurrence(mode="judgment")` — a hard
TypeError against the live dataclass. ADR-393 deleted the field 2026-07-01; all nine
were last touched 2026-06-29 and broke silently the day it landed, staying broken for
30 days. Decisive detail: **all 39 modules IMPORT clean** — the break is
runtime-shaped, so an import check alone would have stayed green over every one.
(The same reason `probe_envelope_collapse_local.py` shipped 28 days dead: its rot was
a function-local import + a deleted env toggle.)

**Suites**: at audit time, **zero of nine Suite-B manifests could fire a paid wake
through `run_eval_suite.py`**:

- The one suite the registry marked CURRENT (`freddie-bare-workspace-steward`)
  crashed at persona resolution — `persona: bare-workspace-steward` was never a
  registry slug (the registered subject is `bare-kernel`,
  `docs/alpha/personas.yaml:434`). It has been fired exclusively through its probe,
  which is why nobody noticed the runner path was dead.
- The same suite's `requires:` used `absent_or_empty:` — not a supported
  `check_preconditions` operator. The unknown-key fall-through treated it as bare
  must-be-present, **inverting the assertion's meaning** into a permanent refusal.
- The eight program suites all assert `governance/_autonomy.yaml` → refused at
  pre-flight after ADR-414 D+E-2 re-homed the hired agent's judgment load-out to
  `agents/{slug}/` — and the deeper block: **zero live hire grants** post D+E-1
  backfill (13 workspaces, 0 minted; the re-hire is a named operator decision).
- Three suites are outright superseded: `alpha-trader-autonomous-loop` (dead
  premise + cites deleted `mode: judgment` and nonexistent `REVIEWER_PRIMITIVES`),
  `author-expected-output-origination` (its single variable migrated twice —
  ADR-366 → `contract/`, ADR-414 → `agents/{slug}/`), and `author-heartbeat-composes`
  (**its thesis was fired and FALSIFIED 2026-06-23** — it stayed armed for five
  weeks after its own falsification).
- The runner itself was NOT stale (no deleted imports, no `mode` dataclass
  dependency — its `mode='judgment'` filters hit the live `execution_events.mode`
  column, which every wake still writes).

**The July drift pattern**: the suite layer's last touch was 2026-07-03; four canon
waves passed over it (ADR-366, ADR-393, ADR-402/403, ADR-414). Every July eval
artifact is probe-driven or click-pass — not one `{date}-{suite}-session/` folder,
the artifact shape the whole discipline doc is built around.

## 2. What landed

### Repairs (runnable floor restored)

| what | fix | validation |
|---|---|---|
| 9 probes | `mode="judgment"` kwarg removed | 9/9 compile; gate green |
| CURRENT suite persona | `bare-workspace-steward` → `bare-kernel` | registry resolves → `4c106786` |
| CURRENT suite requires | `absent_or_empty:` on a directory → two supported `absent:` asserts on the program-marker files | **live pre-flight 4/4 satisfied** on the real bare-kernel workspace |
| `check_preconditions` | unknown operator keys now FAIL LOUDLY with an UNSUPPORTED detail (prior: silent inversion to must-be-present) | falsified: `absent_or_empty` → `ok=False, UNSUPPORTED…` |
| `run_eval_suite.load_suite` | refuses `status: superseded` manifests | falsified: heartbeat suite → SuiteError; current suite loads |
| all 9 manifests | machine-readable `status: current\|dormant\|superseded` + a header naming why and what re-arming requires | gate-checked |
| `SESSION-TEMPLATE.md` | v2 `**Read kind**` field removed (lagged the v3 rework by 8 weeks) | gate-checked |
| `eval-suites/README.md` | registry re-cut: per-suite status + the named migrations each dormant suite owes at re-hire | — |

### Gates (the "clearer testing and validation" ask, made permanent)

**`api/test_probe_staleness_gate.py`** — pure AST, no execution, no DB:
1. Every project-root import in every probe — **including function-local ones** —
   resolves, and every `from X import name` names something the target actually
   defines (the probe_envelope_collapse class).
2. Every `Recurrence(...)` call's kwargs ⊆ the LIVE dataclass fields — derived from
   the class, not a hardcoded list (the ADR-393 class).
   Born red on exactly the 9 known-broken probes; green after the fixes.

**`api/test_eval_suite_gate.py`** — manifests mechanically sound:
1. Parse + schema v3 + required fields + valid `status:`.
2. Persona slug resolves in personas.yaml (the CURRENT-suite crash class).
3. Every referenced scenario file exists.
4. Every `requires:` operator key-set is supported (the silent-inversion class).
5. `current` suites may not assert the ADR-366-migrated `governance/` spellings.
6. Exactly one `current` suite, named — going current is a deliberate act.
7. Template is v3.
   Falsified 5/5 by breach simulation (ghost persona, unsupported operator, missing
   scenario, missing status, migrated path). Bonus receipt: the template check's
   first draft grepped prose and caught its own explanatory comment — narrowed to
   the field form, the standing don't-grep-prose lesson re-earned.

### The two-axis boundary held

Per EVAL-SUITE-DISCIPLINE §0, these gates check only the MACHINE half (does the
instrument physically run). Whether a dormant suite's *thesis* is still true is a
MIND question that stays with the human read — deliberately ungated.

## 3. Operator decisions — named same day, RESOLVED same day

*(As first written this section listed items 1–2 as open; the operator resolved
them within hours. Corrected count: five dormant suites, not six.)*

1. **The five dormant program suites: RETIRED** (operator-directed). Re-pointing
   their `requires:` was unverifiable (zero hire grants — nothing to fire against),
   and the codebase evolved significantly past the dormant-program approach. All
   five deleted; setups, thesis-verdict states (falsifier discipline: which theses
   were FALSIFIED vs DECIDED-ELSEWHERE vs EXERCISED-UNDECIDED), and re-cut guidance
   recorded in `eval-suites/RETIRED-SUITES.md`. Full manifests retrievable at
   `git show 90c7d67:docs/evaluations/eval-suites/<name>.yaml`.
2. **The three superseded manifests: DELETED** (same direction, same record).
3. **The discipline-doc "Reviewer" vocabulary** — ADR-381 D1 relabel-keep-slug makes
   this internal-slug usage; a full re-write is cosmetic and was not done.
4. **Three live owner-grants with no persona row** — resolved with a split, because
   identification changed the picture: `67c5c637` is the operator's own empty
   account (`kvkthecreator@yarnnn.com`, created 2026-01-28, 0 files) → registered
   as persona `kvk-yarnnn` (program: null, bare rig). **`00ab9036`
   (s.colopy@ccgrhc.com) and `4db2e863` (b.tharalson@gmail.com) are REAL EXTERNAL
   SIGNUPS** (0 files, 0 events, but real people) — deliberately NOT registered:
   the persona registry is the probe-target roster, and probes seed, delete, and
   fire funded wakes on their subjects. Making a real user's workspace
   harness-reachable is a safety hazard, not a completeness win.

## Reproduce

```
cd api
python3 -m pytest test_probe_staleness_gate.py test_eval_suite_gate.py -q
# live pre-flight of the repaired CURRENT suite (free, read-only):
#   check_preconditions("4c106786-…", suite.evals[0].requires) -> 4/4 satisfied
```
