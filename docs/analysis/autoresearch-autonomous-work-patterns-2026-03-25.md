# Autoresearch: Autonomous Work Patterns & the Eval Problem

**Date**: 2026-03-25
**Source**: [github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch) (54.6k stars)
**Relevance**: Autonomous agent work loops, eval design, definition of done

---

## What It Is

Karpathy's autoresearch is a minimal framework for autonomous ML research — an AI agent that runs experiments in a loop, keeps improvements, reverts failures, and never stops until a human interrupts. It trains language models on FineWeb-Edu, optimizing val_bpb (validation bits per byte).

The entire system is three files:

| File | Role | Mutability |
|------|------|-----------|
| `prepare.py` | Data, tokenizer, eval harness | Read-only (ground truth) |
| `train.py` | Model, optimizer, training loop | Agent-editable (sole edit surface) |
| `program.md` | Agent instructions | Human-authored |

No framework. No SDK. No orchestration layer. The "agent runtime" is a coding assistant (Claude Code, Codex) with terminal access.

## The Loop

```
LOOP FOREVER:
  1. Read git state (branch tip = current best)
  2. Edit train.py with an experimental idea
  3. git commit
  4. Run train.py (5-min wall clock budget)
  5. grep val_bpb from run.log
  6. If improved → keep (advance branch)
  7. If worse/equal → git reset to previous commit
  8. Log to results.tsv
  9. Never stop. Never ask. The human might be asleep.
```

## Architectural Insights

### 1. Git as State Machine

The branch tip IS the current best. Improvements advance it; failures revert to it. No database, no metadata store, no run tracker. The version control system is the coordination mechanism. The agent can always `git log` and `git diff` to understand what worked.

### 2. Fixed Time Budget as Universal Comparator

Every experiment gets exactly 5 minutes wall clock. This makes architectural changes (different model sizes, batch sizes, attention patterns) directly comparable. The constraint eliminates an entire class of ambiguity — "is this better because it's actually better, or because it trained longer?"

### 3. Untouchable Eval

`evaluate_bpb()` lives in `prepare.py`, which is read-only. The agent literally cannot modify the success criterion. The eval uses a pinned validation shard, fixed token count, vocabulary-independent metric. There is zero room for the agent to Goodhart its way to a better score.

### 4. Context Window as Scarce Resource

Training output is redirected to `run.log`. The agent reads results via `grep "^val_bpb:"` — two lines, not 10,000. Over 100 experiments, this is the difference between a functioning agent and a drowned context window. The pattern: **observe through narrow pipes, reason in clean context.**

### 5. Mechanical Quality Ratchet

No judgment needed for keep/discard. Lower val_bpb = keep. Period. The simplicity criterion is in the prompt: *"0.001 improvement that adds 20 lines of hacky code? Not worth it. 0.001 from deleting code? Definitely keep."* Quality control is structural (metric ratchet) + behavioral (simplicity preference in instructions).

### 6. Crash Recovery Without Human

Distinguish "dumb bugs" (fix and retry) from "fundamentally broken ideas" (log as crash, move on). Plus a 10-minute hard timeout (2x budget) to kill hung processes. The agent never gets stuck.

## The Eval Problem: Why This Works for ML and Doesn't for Knowledge Work

Autoresearch's elegance comes from a property that ML optimization has and knowledge work doesn't:

**A single, scalar, objective, computable metric.**

val_bpb is:
- **Scalar** — one number, lower is better
- **Objective** — no human judgment needed to compute it
- **Deterministic** — same code + same data = same score (within floating point)
- **Cheap** — computed in seconds, not days
- **Aligned** — lower val_bpb actually means "better language model" (not perfectly, but usefully)

Knowledge work has none of these properties. When a YARNNN agent produces a competitive landscape briefing, a Slack digest, or a research synthesis:

- **No scalar metric** — quality is multi-dimensional (accuracy, relevance, completeness, insight depth, actionability, tone)
- **Subjective** — two readers may disagree on whether a briefing is good
- **Non-deterministic** — the "right" output changes with context, timing, audience state
- **Expensive to evaluate** — requires a human to read and judge, or a more capable model to assess
- **Alignment is fuzzy** — optimizing for any single proxy (length, citation count, readability score) would produce pathological outputs

This is the fundamental challenge: **autoresearch can ratchet because its eval is a function. Knowledge work eval is a judgment.**

## What YARNNN Can Learn

Despite the eval gap, several patterns transfer directly:

### Patterns That Map

| autoresearch | YARNNN | Status |
|---|---|---|
| `program.md` as skill file | TASK.md + AGENT.md | Implemented (ADR-138) |
| Git as accumulated state | Workspace filesystem | Implemented (ADR-106/119) |
| "NEVER STOP" loop | Pulse cadence (ADR-126) | Implemented |
| Context protection (grep, log redirect) | Workspace search over full corpus | Implemented |
| Crash recovery protocol | Pulse Tier 1 deterministic checks | Implemented |
| Simplicity criterion in instructions | Agent behavioral directives | Implemented |
| Fixed time budget | Fixed work budget (ADR-120) | Implemented |

### The Eval Gap — Where YARNNN Must Invent

Autoresearch's keep/discard is binary and mechanical. YARNNN's equivalent needs to be:

1. **Multi-signal** — edit distance (did the user change the output?), approval rate, time-to-approve, feedback sentiment, re-delivery rate
2. **Temporal** — a good briefing today might be bad tomorrow if the landscape shifted
3. **Relative to prior self** — is this agent getting better at serving THIS user? (ADR-117 feedback trajectory)
4. **LLM-assessable where human-assessment is impractical** — self-assessment (ADR-128) as cheap proxy, human correction as ground truth

The current YARNNN eval surface:
- **Tier 1 (deterministic)**: Did content change since last run? Is budget available? Was there a recent run? → These are autoresearch-style mechanical checks
- **Tier 2 (Haiku self-assessment)**: Does the agent believe it has something worth saying? → Cheap LLM proxy, roughly analogous to a "does this compile?" check
- **User feedback loop**: Approve/reject/edit → the actual eval, but expensive and async

What's missing: **a ratchet mechanism for knowledge quality.** Autoresearch keeps the branch tip at the best-known state. YARNNN agents don't have an equivalent — there's no "this output was strictly better than the last one, so lock it in." The feedback distillation to `preferences.md` (ADR-117) is the closest analog, but it's a preference accumulator, not a quality ratchet.

### Possible Directions

1. **Output comparison as eval** — after generating, compare to previous best output using a judge model. Keep structural improvements, flag regressions. Not a scalar metric, but a pairwise preference signal.

2. **Workspace as ratchet** — the accumulated `memory/`, `thesis.md`, `preferences.md` files are the equivalent of autoresearch's branch tip. The agent's workspace quality should monotonically improve even if individual outputs vary. The ratchet is on knowledge, not output.

3. **User correction as ground truth** — every edit is a training signal. The agent that requires fewer edits over time is improving. Edit distance trend IS the metric, just lagging and noisy.

4. **Cadence-aware eval** — for recurring work, consistency matters. A daily briefing that's great Monday, mediocre Tuesday, great Wednesday is worse than one that's consistently good. Variance in quality is itself a quality signal.

## The Deeper Insight

Autoresearch works because **the environment makes the right thing easy and the wrong thing impossible.** The eval can't be gamed. The time budget is fixed. Improvements ratchet. Failures revert. The constraints ARE the coordination mechanism.

YARNNN's version of this: **the workspace is the ratchet, feedback is the eval, and the agent's accumulated knowledge is the branch tip.** The agent can't un-learn a preference. It can't un-observe a pattern. Each run adds to the substrate, and the substrate makes the next run better.

The difference: autoresearch optimizes a function. YARNNN develops a relationship. Both are valid forms of autonomous improvement — but they require fundamentally different notions of "better."
