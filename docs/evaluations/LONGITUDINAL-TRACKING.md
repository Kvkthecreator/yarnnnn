# Longitudinal Tracking — the third evaluation surface (tenure observation)

> **Status**: framing proposed 2026-06-10 (operator-articulated). Names the surface that [`EVAL-PHILOSOPHY.md`](EVAL-PHILOSOPHY.md) implies but [`EVAL-ARCHITECTURE.md`](EVAL-ARCHITECTURE.md) lacks. Hat-B (external developer surface — toolchain that probes the system). No system-canon change; this is an evaluation-surface definition.
>
> **Where this sits.** EVAL-PHILOSOPHY says *what we're testing* (the Reviewer is a self-running Claude Code **carrying standing intent across time** — "ownership over tenure," DP24). EVAL-ARCHITECTURE gives two surfaces — Suite A (agnostic machine) + Suite B (specific thesis) — but **both are episodic: fire one situation, read once.** Neither observes tenure. This doc names the missing surface: the **continuous tenure monitor**. It is a sibling to Suite A / Suite B, distinguished not by machine-vs-mind but by **episodic-vs-continuous** and **harness-fired-vs-scheduler-fired**.

---

## §1 The problem this surface exists to solve

The self-improving thesis — "agents that improve with tenure" (FOUNDATIONS DP24, ADR-327 D6) — is **inherently longitudinal**: it is a claim about a *curve over weeks*, not a *decision in a situation*. The episodic suites cannot prove it, no matter how adversarial, because:

- A Suite-B eval **manufactures** the situation (`@now` tokens, seeded `_calibration.md`, `append_recurrence`). It is a *simulation of tenure* compressed into one fired wake. The 2026-06-09 ADR-327 calibration eval is the canonical example: we seeded a fake 38-fire history so a one-shot eval could test a thing that is really about *earned* history. **It worked — and that is its ceiling.** It proves the *mechanism* (the Reviewer archives a dead cadence on evidence); it cannot prove the *thesis* (the agent's real cadence choices, made off its own earned calibration trail, improve outcomes over time).
- "Improves with tenure" can only be **lived, not fired.** The proof is watching a workspace accumulate its *own* calibration trail from *real* fires and reading whether the curve bends the right way.

**The episodic harness forced into a longitudinal question is the root of the eval-framework churn** (≈7 first-principles reframes across 2026-05-20 → 06-09). Each reframe reached for bigger, more longitudinal setups and bolted more machinery onto an episodic harness to fake the passage of time. Naming the continuous surface as a separate thing stops that forcing.

---

## §2 The two surfaces, by purpose (the regression-vs-monitoring split)

This is standard software practice: **regression tests** (run on every change, fast, deterministic) are a different thing from **production monitoring** (continuous, observes the live system). The eval framework conflated them because it only had the fire-and-read shape.

| | **Dev-eval suite** (Suite A + Suite B) | **Longitudinal track** (this doc) |
|---|---|---|
| Analogue | regression test | production monitoring |
| Unit | one fired situation, read once | a running workspace, observed over weeks |
| Time | **simulated** (`@now`, seeded trails, `append_recurrence`) | **real** (earned calibration history) |
| Clock owner | **harness / Claude** (manually advances `@now`, fires wakes) | **the system** (Render cron → wake_queue → drainer, unattended) |
| Question | "is the mechanism safe + correct to *let run*?" | "is it *actually improving* as it runs?" |
| Cadence | on every architectural change (ADR lands → re-run gate) | continuous; read periodically |
| Output | green/red gate + prose finding (per [`EVAL-SUITE-DISCIPLINE.md`](EVAL-SUITE-DISCIPLINE.md) §6) | a dated tracking log of the trajectory, deploy-marker-stamped (§4) |
| Proves | the **mechanism** works | the **thesis** is true |
| Hat | B | B (a report over substrate, not a fired probe) |

**The composition rule:** the dev-eval suite is the **pre-flight gate** for the longitudinal track. Before you trust a tenure segment as evidence, the mechanism must pass the episodic gate (does it archive a dead cadence? refuse pressure? queue irreversible actions?). Then the longitudinal track observes whether the *earned* loop actually improves. Gate before tenure; watch during tenure.

---

## §3 The paradox, and its resolution (deploy-markers)

**The paradox the operator named (2026-06-10):** the longitudinal track wants a *stable measurand* (let it run for weeks), but the architecture *keeps changing underneath* (refactors land weekly, and always will — this is normal product evolution). Without resolving this, every behavior shift three weeks in is ambiguous: *is this the agent improving, or an ADR that landed in week 2?*

**The resolution is the same one production monitoring uses: don't freeze the architecture — label the timeline.**

A monitoring dashboard does not demand a frozen codebase; it puts **deploy-markers** on the timeline. When a metric moves, you check whether a deploy-marker sits under the move. The longitudinal track does the same: **every observation is stamped with the commit / canon-version the workspace ran under for that segment.** "This calibration-curve segment ran under canon-as-of `<commit>`." Improvement and architectural-shift become distinguishable **by construction**, not by argument.

So the paradox dissolves: structural/architectural/refactoring change continues freely on the existing side (regression-gated by the dev-eval suite on each change), AND the qualitative accumulative workspace is tracked continuously (with deploy-markers making each segment attributable). The two axes stop contaminating each other.

---

## §4 How the longitudinal track works (mechanics)

The track is a **report over substrate that already exists** — not new instrumentation. Confirmed 2026-06-10 against the live kvk workspace:

- The improvement **trajectory is not pre-computed into any file** — `_calibration.md` is a rolling-window *snapshot* (overwritten diff-aware every tick), not a curve.
- But the trajectory is **fully reconstructable** from substrate that is retained over all time:
  - `workspace_file_versions` — the ADR-209 revision chain. The ground-truth curve is the diff-sequence of `_money_truth.md` revisions (kvk: 69 revisions over 20 days). Cadence-authoring history is the `_recurrences.yaml` / `principles.md` revision chain, attributed.
  - `execution_events` — the immutable cost/outcome ledger (kvk: 9,547 events, 83 judgment, over 20 days).
- So "did expectancy improve after the Reviewer archived the dead cadence" is a **query across the revision history + the events ledger over the run window**, joined to the deploy-marker timeline.

**The gap is presentation, not retention** — nothing is lost; there is just no curve *view*. Closing it is a report/query, optionally promoted to a first-class kernel mirror later **only if running the track proves it load-bearing** (demand-pull, not speculation).

> **The reconstruction report now has an instrument: [`TENURE-READ.md`](TENURE-READ.md) (2026-06-11).** It is the MIND-axis companion to the soak's `SURVIVAL-QUERIES.md` (MACHINE axis) — three reads over retained substrate (the ground-truth-curve revision chain, the self-amendment trail, the intent-coherence prose read), parameterized by the program's `substrate_abi.ground_truth` declaration (ADR-188/ADR-330 agnosticism: trader → `_money_truth.md`, author → `_voice.md`, generic → no curve, see TENURE-READ §5). Survival gates; quality is the thesis evidence. The instrument's first run (alpha-trader-2, 2026-06-11) validated the shape AND surfaced a real judgment-effect divergence (a day-1 cadence edit that nulled `track-universe`'s RTH schedule) that the green survival check structurally could not see — the qualitative half earning its keep on run one.

### §4.1 Who owns the clock, and how Claude fits

The crux of "how does a session-bound assistant handle a weeks-long phenomenon": **Claude does not own the loop — the system does.**

- **The system drives time.** The Render cron scheduler (`*/5 * * * *`) walks due recurrences → `wake_queue` → `wake_drainer` → `invoke_reviewer`, unattended, with the ADR-327 budget gate + single-in-flight + stale-lock reclaim as continuous-run guards. No human, no harness, no Claude session is needed for the workspace to *live its tenure*. (Proven ≈36h on kvk; architected for weeks — see §6 caveat.)
- **Claude is the periodic reader.** When invoked — manually, or via a `/schedule`d routine that wakes every N days — Claude runs the §4 trajectory-reconstruction query, diffs the substrate since the last read, and appends a dated, deploy-marker-stamped entry to the tracking log. A thin observer riding on the system's clock. *This is the one place a scheduled-Claude routine genuinely fits: not to drive the agent, but to read its accumulated work and report the curve.*
- **Claude is the regression-gate runner.** When an ADR lands, Claude re-runs the dev-eval suite to confirm the mechanism survived the change — before trusting the next tenure segment.

The time axis is handled by **separating the clock (system-owned, continuous) from the reading (Claude-owned, periodic).** Claude never needs to "stay awake for a week."

---

## §5 Discipline rules (the standard testing best-practices, applied)

1. **Episodic vs continuous is the surface seam.** A surface is either the dev-eval suite (fired, read once, regression-gates a change) or the longitudinal track (scheduler-driven, read periodically, monitors tenure). If you're advancing `@now` by hand, you are in the episodic suite — that is simulation, useful for the gate, never the thesis proof.
2. **Gate before tenure.** A tenure segment is only evidence if the mechanism passed the episodic gate for the canon it ran under. Never read improvement off a segment whose mechanism gate is red.
3. **Every observation carries its deploy-marker.** No tracking-log entry without the commit/canon-version stamp. An unstamped observation cannot resolve the §3 paradox and is not evidence.
4. **The track is a report over existing substrate first.** Reconstruct from `workspace_file_versions` + `execution_events`. Promote to a purpose-built curve-mirror only when running the track proves the ad-hoc query insufficient (demand-pull).
5. **The system owns the clock; Claude reads.** Do not build a Claude-driven synthetic clock to fake tenure — that is the episodic harness again. The scheduler is the clock. (A synthetic-clock "compressed week" remains a legitimate *episodic* tool for the gate, but it does not produce longitudinal evidence.)
6. **Survival precedes improvement.** A planned multi-week unattended run must first demonstrate the system *survives* tenure (no silent-wake, no stuck locks, no cost runaway, correct market-holiday handling) before its curve is read as *improvement* evidence (§6).

---

## §6 Known gating gaps (honest state, 2026-06-10)

Feasibility is green but not yet exercised end to end. Before the longitudinal track can produce thesis-grade evidence:

- **Multi-week unattended survival is architected but never validated.** Proven ≈36h on kvk; all evals to date were *harness-fired*, never a planned *scheduler-fired* multi-week run with explicit survival criteria (zero silent-wakes, zero stuck locks, budget not exhausted, market-holiday next-fire correct). Rule 6: survival before improvement.
- **The curve view does not exist yet** (§4 — presentation gap; the data is retained). *Partially closed 2026-06-11*: [`TENURE-READ.md`](TENURE-READ.md) is the reproducible reconstruction-report instrument (the MIND-axis qualitative read); a built curve-*view* component remains demand-pull (promote only if the ad-hoc query proves insufficient across real reads, §5 rule 4).
- **Meaningful capital loops are slow** (days-to-a-week between genuine trader signals per the alpha-trader session notes) — a "boring week with no signals" tests survival, not the judgment loop. The track's window must be long enough to capture real judgment events.

These are the prerequisites, not blockers — each is a concrete next step, not a redesign.

---

## §7 Relationship to the rest of the eval canon

- **Extends** EVAL-PHILOSOPHY §2 (standing-intent-across-time / ownership-over-tenure) — names the surface that observes the thing the philosophy says is the product.
- **Sibling to** EVAL-ARCHITECTURE Suite A / Suite B — adds the episodic-vs-continuous axis the two-suite seam (agnostic-vs-specific) did not cover. Does not supersede them; the dev-eval suite is the longitudinal track's pre-flight gate (§2 composition rule).
- **Reuses** EVAL-SUITE-DISCIPLINE §6 prose-read shape for the tracking-log entries, and README's substrate-receipt discipline (every claim carries a revision_id / execution_event id / reproducible query).
- **No new harness apparatus** beyond a trajectory-reconstruction report — deliberately, per the over-investment lesson (the best historical eval session was the one that ignored the apparatus and read substrate in prose). The one instrument that exists is [`TENURE-READ.md`](TENURE-READ.md) — and it is exactly a reproducible substrate-prose-read, not apparatus.

## §8 The two soak instruments (the MACHINE + MIND halves)

A longitudinal soak runs two complementary instruments per read, both over the same window + deploy-marker:

| Instrument | Axis | Question | Output |
|---|---|---|---|
| `longitudinal-soak-*/SURVIVAL-QUERIES.md` | MACHINE | "did it run?" (cycles close, no faults) | 6 SQL checks, green/red → survival verdict |
| [`TENURE-READ.md`](TENURE-READ.md) | MIND | "was the reasoning good, and is it improving?" | 3 substrate reads → prose finding + tenure verdict |

**Survival gates quality** (§5 rule 2): never read a TENURE-READ as improvement evidence on a window whose survival pass is red. The tenure verdict ladder — `SURVIVING` (machine) → `SURVIVING + COHERENT` (mind reasons well, no curve yet) → `IMPROVING` (the DP24 thesis, only on an earned ground-truth ledger) — is the soak's progress measure. Most early reads land at COHERENT; `IMPROVING` requires accumulated outcomes. The generic/bare-kernel soak caps at COHERENT by construction (no domain ground truth to improve against — TENURE-READ §5).
