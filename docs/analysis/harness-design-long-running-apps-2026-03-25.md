# Harness Design for Long-Running Application Development — Analysis

> Source: [Anthropic Engineering — Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps)
> Author: Prithvi Rajasekaran (Anthropic Labs), March 24, 2026
> Analysis date: 2026-03-25

## Article Summary

Multi-agent GAN-inspired architecture for complex, long-duration tasks. A **generator-evaluator** loop where separate agents produce and critique work, connected via structured file handoffs.

### Core Problem

1. **Context degradation** — models lose coherence as context fills; some exhibit "context anxiety" (prematurely wrapping up)
2. **Self-evaluation bias** — agents consistently overestimate own work quality on subjective tasks

### Architecture: Three-Agent System

| Agent | Role | yarnnn Parallel |
|-------|------|-----------------|
| **Planner** | Brief → detailed spec; high-level design over implementation | Composer (ADR-111) — assessment → creation/adjustment |
| **Generator** | Iterative implementation with "sprint contracts" | Agent execution pipeline — headless runs with workspace context |
| **Evaluator** | Playwright-based testing, hard thresholds, bug reports | PM quality assessment (ADR-121) — assess_quality, assembly gating |

Communication via **structured file handoffs** — preserves context across agent resets.

### Key Results

- Solo agent: 20 min, $9 → broken core functionality
- Full harness: 6 hrs, $200 → functional, polished output
- Opus 4.6 simplified: 3h50m, $125 → dropped per-sprint eval, single final QA pass

### Design Principles

1. **Separate generation from evaluation** — external feedback > self-improvement
2. **Decompose subjective judgment** — encode design principles as concrete, gradable criteria
3. **Structured handoffs** — file-based communication preserves context across resets
4. **Calibrate continuously** — align evaluator via examples, not generic instructions
5. **Expect harness evolution** — model improvements shift which scaffolding is essential

---

## Relevance to yarnnn

### Already Aligned

yarnnn's architecture independently converges on several of these patterns:

| Anthropic Pattern | yarnnn Implementation |
|-------------------|----------------------|
| Generator-evaluator separation | Agent (generate) → PM (assess_quality, steer) — ADR-121 |
| Structured file handoffs | Workspace filesystem — agents communicate via workspace_files, contribution briefs, manifests — ADR-106, ADR-119 |
| Planner as spec generator | Composer translates portfolio signals → project scaffolds with objective/team/process — ADR-111, ADR-122 |
| Sprint contracts | PM work_plan.md with phases and budget — ADR-120 |
| Evaluator calibration via examples | Feedback distillation → preferences.md; edit history as calibration signal — ADR-117 |
| Context resets across agents | Each agent run is a fresh context with workspace injection — ADR-080, ADR-106 |
| Harness simplification with model improvements | ADR-126 pulse tiers: Tier 1 deterministic (zero LLM), Tier 2 Haiku (cheap), Tier 3 only when needed |

### Gaps & Opportunities

#### 1. Explicit Evaluation Criteria (High Priority)

Anthropic's evaluator uses **four explicit grading dimensions** with hard thresholds. yarnnn's PM quality assessment (ADR-121) is currently free-form LLM judgment without structured criteria.

**Opportunity**: Define per-project-type evaluation rubrics in PROCESS.md — e.g., a briefer project could grade on: completeness (all sources covered), currency (no stale data), clarity (readable by stated audience), actionability (decisions enabled). PM's `assess_quality` action would score against these dimensions rather than making holistic judgments.

**Fits**: ADR-136 (PROCESS.md as output spec) + ADR-137 (pipeline evaluate step).

#### 2. Evaluator Skepticism Calibration

> "Out-of-the-box, Claude approved mediocre work"

This matches yarnnn's observed behavior — PM quality assessments tend toward approval. The article's solution: **few-shot examples with detailed score breakdowns**.

**Opportunity**: Seed PM's `memory/evaluation_examples.md` with calibration examples showing what "good enough" vs "needs revision" looks like for each project type. The project type registry (ADR-130) could carry default evaluation exemplars.

#### 3. Context Reset as Feature, Not Bug

The article emphasizes that context resets (full clear, not compaction) improved output quality for earlier models. yarnnn already does this — each headless agent run starts fresh with curated workspace context injection. This validates the architectural choice in ADR-080.

**Implication**: Resist the temptation to carry conversational state into headless runs. The workspace IS the persistent context; the LLM context should be fresh each cycle.

#### 4. Harness Simplification Principle

> "Find the simplest solution possible, and only increase complexity when needed. Re-examine harnesses when new models release."

yarnnn's ADR-126 pulse tiers embody this — Tier 1 is zero-LLM deterministic checks, Tier 2 is cheap Haiku, Tier 3 is full coordination. The principle extends to ADR-137's complexity-adaptive pipelines (simple/standard/complex).

**Action item**: When Opus 4.6+ capabilities mature, audit whether PM coordination pulses (Tier 3) can simplify further — the article shows Opus 4.6 dropped per-sprint evaluation entirely.

#### 5. Prompt Language Shapes Output Character

> Phrases like "museum quality" steered designs toward specific visual convergences

This has implications for yarnnn's agent instructions and project objectives. The objective field in PROJECT.md (ADR-123) directly shapes output character. Worth noting in prompt engineering guidance — abstract quality descriptors may cause convergence; specific, concrete criteria produce more distinctive outputs.

### Not Applicable / Different Context

- **Playwright-based testing**: Anthropic's evaluator interacts with live UI. yarnnn's agents produce knowledge artifacts (text, HTML), not interactive apps. Evaluation is content quality, not functional correctness.
- **Sprint negotiation**: The generator-evaluator negotiate sprint scope before implementation. yarnnn's PM writes contribution briefs (one-directional steering), which is simpler and sufficient for knowledge work. Negotiation adds latency without clear benefit for recurring digest/analysis workflows.
- **$200 cost tolerance**: The article's full harness costs $200 for a single run. yarnnn targets ~$0.17-0.50/cycle (ADR-137). The GAN loop's multiple evaluation rounds would blow the budget for recurring work. yarnnn's approach (single PM evaluate step, not iterative refinement loops) is the right tradeoff for recurring cadence.

---

## Takeaways for Implementation

1. **Structured evaluation rubrics** in PROCESS.md — most impactful near-term improvement
2. **Evaluation calibration examples** seeded per project type — addresses the "approves mediocre work" problem
3. **Validate fresh-context-per-run** as intentional architecture (don't regress toward conversational agent runs)
4. **Audit scaffolding** on each model upgrade — what was essential for Sonnet 4.5 may be unnecessary for Opus 4.6
5. **Prompt specificity** in objectives — concrete criteria > abstract quality descriptors
