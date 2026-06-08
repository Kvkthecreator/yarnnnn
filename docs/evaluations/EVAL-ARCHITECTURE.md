# Eval Architecture — first principles (2026-06-07)

> **Written from scratch, NOT amended onto the prior framework.** The operator's diagnosis (2026-06-07): the prior structure (`read_kind` taxonomy, M-cell / P-cell posture tables, the situation-cell criterion) was legacy-weighted — it kept trying to *pre-enumerate answers* and to *fit new thinking onto old cells*. This doc derives the eval architecture from the [`EVAL-PHILOSOPHY.md`](EVAL-PHILOSOPHY.md) metaphor (filesystem=repo; Reviewer=self-running-Claude-Code + standing intent) with no obligation to preserve the prior apparatus. §5 inventories what that makes legacy.
>
> **Status**: proposed first-principles architecture, 2026-06-07. Supersession of the legacy apparatus (§5) is named, not yet executed — operator ratifies, then Singular-Implementation cleanup follows.

---

## §1 The first-principles question

If the Reviewer is *a self-running Claude Code carrying standing intent over a repo* (EVAL-PHILOSOPHY §1–2), then "how do you evaluate it?" is the same question Anthropic asks of Claude Code itself, plus the standing-intent layer Claude Code lacks. A coding-agent harness has exactly two kinds of test, and they fall on **one clean seam: workspace-agnostic vs. workspace-specific.**

- **"Does the machine work — for ANY repo?"** Permissions enforce, files read/write, tools land, the runtime doesn't crash. Repo-agnostic. Has a right answer. → **Suite A.**
- **"Does it do the RIGHT thing for THIS repo/task?"** Judged against the task's intent, by examining what the agent actually did. Repo-specific. No single right answer — a trace read against a thesis. → **Suite B.**

That seam is already visibly present in the repo, unnamed: every existing eval-suite is `persona`-bound (specific); the agnostic machine layer has no persona because it's *for any workspace*. **Persona-boundness IS the agnostic/specific signal.** The prior framework split suites by `read_kind` (a MIND-only taxonomy) and punted the entire machine layer to scattered `api/test_*.py` — so it had no first-class home for Suite A and over-structured Suite B.

---

## §2 The two suites

### §2.A Suite A — Mechanical (workspace-AGNOSTIC, deterministic, the kernel machine)

**Question**: does the self-running-Claude-Code *machine* behave correctly, for any workspace, independent of any mandate?

**Object**: the kernel — five-root permission topology, the revision chain + attribution, the wake/dispatch path, primitive syscalls landing at the right path, single-lane queue serialization, cycle-closure mechanics, pace gating. EVAL-PHILOSOPHY **layers 1–2**.

**Has a right answer?** Yes — deterministic, CI-runnable. This is `api/test_*.py` territory, and it is **already substantially built** (the ADR-numbered gates: `test_adr320_permission_topology`, `test_adr298_phase1_wake_queue`, `test_adr321_path_native_primitives`, `test_revision_cross_workspace_isolation`, `test_silent_wake_trigger_fix`, …).

**What's new here vs. the prior framing**: Suite A is named as a *first-class eval surface*, not "the stuff that isn't eval." It is **workspace-agnostic by construction** — a Suite-A test that references `trader`/`alpaca`/`nvda` is mis-filed (it belongs in Suite B's mechanical sub-layer, §3). The discipline: **a Suite-A test must pass on an empty workspace, an author workspace, and a trader workspace identically.** That's the agnosticism gate.

**Method**: control input → assert exact substrate output → green/red. No prose read. No thesis. The machine either carries the situation through or it doesn't.

### §2.B Suite B — Thesis-trace (workspace-SPECIFIC, forensic, the agent's mind against its mandate)

**Question**: does *this* agent, holding *this* mandate, behave the way its **thesis** says it should — read by forensically breaking down its tool-calls, rationale, logs, and outputs?

**Object**: the standing-intent layer (EVAL-PHILOSOPHY **layers 3–4**) — judgment-within-mandate AND intent-ownership-across-the-gap — but **NOT as a cell table**. Suite B is an **investigation**, not a rubric:

1. **Start from the thesis** — the workspace's assumed behavior + posture, derived from its MANDATE + principles + the agent's design intent. *What should this agent do, and why?* (the operator writes this down BEFORE the run — it is the criterion, README rule 1).
2. **Capture the full trace** — tool-calls (which primitives, in what order, with what args), rationale (the wake reasoning), logs (`execution_events`: wake_source / mode / status / tokens), outputs (substrate writes, proposals, verdicts).
3. **Read the trace against the thesis** — does the trace *embody* the thesis? Where it diverges, *why* (cause a substrate / b reasoning / c envelope / d canon)? This is forensics: you are reconstructing the agent's reasoning from its receipts and asking whether a mandate-holder would recognize it as their own judgment.

**Has a right answer?** No — a spectrum read as prose, against the thesis. The posture vocabulary (if used at all) is *descriptive language for the write-up* ("it stood down on freshness — cell-D-ish"), never the structure the read resolves into. **This is the deepest break from legacy**: the suite does not pre-enumerate the situations and grade against cells; it presents the thesis + the trace and investigates coherence.

**Method**: the operator-proxy fires the agent into a thesis-relevant situation; the harness captures the full trace; the operator reads the trace against the thesis and writes a prose finding. The harness's job is **trace completeness** (every tool-call, every log, every output captured and legible), not classification.

---

## §3 The subtlety the legacy framing fused: THREE axes, not two

The agnostic/specific seam is clean, but "mechanical" and "agnostic" are **different axes** — the prior framing fused them, which is why `test_alpha_trader_pipeline_e2e.py` (deterministic but trader-SPECIFIC, 23 trader refs) had no clean home. There are three places a test can sit:

| | Mechanical (deterministic, right answer) | Thesis (forensic, no single answer) |
|---|---|---|
| **Agnostic** (any workspace) | **Suite A** — the kernel machine (`test_adr320`, wake queue, topology, revision chain) | — (a thesis is always workspace-specific by definition) |
| **Specific** (this program) | **Suite B-mechanical** — the program's PIPELINE (`test_alpha_trader_pipeline_e2e`, `test_risk_gate_rule_battery`, `test_market_hours_gate`) — deterministic, but binds the program | **Suite B-thesis** — the agent's MIND against its mandate (the forensic trace read) |

So **Suite B has two sub-layers**: the program's *mechanical* pipeline (deterministic `test_*.py`, but program-specific — "does THIS program's machine carry a signal to a fill?") and the agent's *thesis* trace (forensic prose — "does the agent reason like THIS mandate-holder?"). The two-axis MACHINE/MIND model (EVAL-SUITE-DISCIPLINE §0) is the *within-Suite-B* discipline: a trader plumbing bug is Suite-B-mechanical (write a `test_*.py`), a trader judgment question is Suite-B-thesis (forensic read). **The whole-system seam is agnostic-vs-specific (A vs B); the within-B seam is mechanical-vs-thesis.**

This is the placement legacy lacked:
- `test_adr320_permission_topology` → **Suite A** (agnostic kernel).
- `test_alpha_trader_pipeline_e2e` → **Suite B-mechanical** (trader pipeline — deterministic but specific).
- the forensic read of a trader wake's reasoning → **Suite B-thesis**.

---

## §4 What this makes the trader work

The alpha-trader eval is **Suite B** (workspace-specific). Its two sub-layers:

- **B-mechanical** (already green): `test_alpha_trader_pipeline_e2e.py` (the trade fires) + `test_trading_pipeline_architecture.py` (indicators/casing) + `test_risk_gate_rule_battery.py` + `test_market_hours_gate.py`. The program machine works. **This is done.**
- **B-thesis** (the actual remaining work): the forensic read. Start from the trader thesis — *"a systematic trader holding this mandate proposes signal-attributed, risk-sized trades when conformance holds; owns its own readiness gaps (authors cadence + standing_intent) rather than passively waiting or confabulating readiness; revises rules only on ground-truth, never on pressure."* Then fire the agent into thesis-relevant situations and **break down its tool-calls, rationale, logs, outputs** against that thesis.

**The posture cells dissolve into the thesis statement.** What I built as the A–F situation table + conformance-vs-outcome decomposition becomes *one paragraph of thesis* + a forensic read that examines whether the trace embodies it. The Q2 "decision" (conformance-vs-outcome) is still *true* (it's correct canon) — but it stops being a cell to grade against and becomes *something the forensic reader knows to look for* in the trace. The criterion is the thesis; the cells are reading aids.

---

## §5 Legacy inventory — what this supersedes (Singular Implementation)

Named for operator ratification; cleanup follows ratification.

| Legacy artifact | Fate under the two-suite model | Rationale |
|---|---|---|
| `read_kind` taxonomy (judgment_coherence / substrate_responsiveness / stewardship_coherence) | **SUPERSEDE** → these are *facets of the Suite-B-thesis read*, not suite types. A thesis read naturally covers judgment, responsiveness, and stewardship as it follows the trace. | The taxonomy split the MIND into three suite-shapes; the forensic read is one activity that touches all three. |
| Posture-cell tables (M1–M9, P1–P5, criterion v2 A–F + conformance-split) | **DEMOTE to descriptive vocabulary** — kept as *names for what you saw* in a write-up, deleted as *suite structure*. | EVAL-SUITE-DISCIPLINE §4 already says cells are "a reading aid, not a grading scale" — this finishes that move by removing them from the suite's spine entirely. |
| `alpha-trader-autonomous-loop.criterion.md` (the cell-table criterion) | **REWRITE** → a thesis statement + forensic-read protocol, not a cell table. | The cells were pre-enumerated answers; the thesis + trace forensics is the first-principles shape. |
| EVAL-SUITE-DISCIPLINE §0 two-axis model | **KEEP, re-home as within-Suite-B discipline** (§3 above). | The MACHINE/MIND split is correct *inside* the specific suite; it's not the top-level seam (agnostic/specific is). |
| The `*.yaml` suite manifests (`requires` / `prior` / `accumulates` / pre-flight) | **KEEP** — the firing + pre-flight + trace-capture mechanics are sound; only the *organizing taxonomy* (`read_kind`) and the *cell criterion* change. | The harness mechanics (the 2026-06-07 fixes, `@now`, pre-flight `requires`) are Suite-B's delivery engine and are correct. |
| `api/test_*.py` machine tests | **PARTITION** → agnostic ones are Suite A; program-specific ones are Suite B-mechanical. No file moves required; the partition is conceptual (a naming/doc convention: `test_adr*` = Suite A kernel; `test_<program>_*` = Suite B-mechanical). | The tests are correct; they just lacked a two-suite home. |
| EVAL-PHILOSOPHY.md four layers | **KEEP** — layers 1–2 = Suite A; layers 3–4 = Suite B (mechanical + thesis). The two-suite model is the *operational* expression of the four-layer *conceptual* model. | The philosophy is the why; this is the how. |

---

## §6 The discipline rules (first-principles, replacing the cell-grading instinct)

1. **The whole-system seam is agnostic-vs-specific.** A test/eval is either Suite A (passes identically on any workspace) or Suite B (bound to a program's thesis). If you can't say which, you haven't scoped it.
2. **Suite A is deterministic and agnostic — no prose, no thesis, no persona.** A Suite-A test that names a program is mis-filed.
3. **Suite B is forensic, not rubric.** Declare the thesis (assumed behavior + posture) BEFORE the run. Capture the full trace. Read the trace *against the thesis*. Cells are vocabulary, never structure.
4. **Within Suite B, mechanical-vs-thesis is the EVAL-SUITE-DISCIPLINE §0 two-axis split.** A program plumbing bug → a deterministic `test_*.py` (B-mechanical). A judgment question → a forensic read (B-thesis). Don't debug a B-mechanical bug through a B-thesis read (the recurring 2026-05/06 trap).
5. **The harness's job in Suite B is trace completeness + legibility, not classification.** Every tool-call, every `execution_event`, every substrate write, every verdict — captured and readable. The human does the forensics.
6. **Criterion = thesis (README rule 1, taken literally).** The Suite-B criterion is the workspace's thesis; adherence is read by trace forensics. An un-stated thesis = a substrate snapshot, not an eval.

---

## §7 What changes operationally (for the trader run)

- **Suite A**: confirm the agnostic kernel gates pass (they do). Optionally formalize the partition (doc convention naming which `test_adr*` are the kernel-machine suite). No new work to run the trader.
- **Suite B-mechanical**: already green (the trade fires). Done.
- **Suite B-thesis**: rewrite `alpha-trader-autonomous-loop.criterion.md` from a cell table to a **thesis statement + forensic-read protocol** (what to look for in tool-calls / rationale / logs / outputs, with the gap-stance and conformance-vs-outcome as *things-to-watch-for*, not cells). Then the run is a forensic read of the agent's trace against that thesis — which is what "self-running, self-improving trades" actually demands: not "did cell B fire" but "does the agent's whole trace read like a trader who owns this operation."

This is the rework. The cell-grading apparatus was the legacy weight; the thesis-trace forensic read is the first-principles replacement.
