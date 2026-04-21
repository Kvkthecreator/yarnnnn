# Dual-Objective Discipline — How Alpha-1 Observations Stay Honest

> **Status**: Canonical.
> **Scope**: Alpha-1 and forward. Defines how observations are captured,
> classified, and rolled up so we validate *both* objectives at once
> without drifting toward whichever is nearest the keyboard.
> **Related**:
> - [ALPHA-1-PLAYBOOK.md](./ALPHA-1-PLAYBOOK.md) §7 friction-capture
>   loop now cross-references this doc for the extended schema
> - [CLAUDE-OPERATOR-ACCESS.md](./CLAUDE-OPERATOR-ACCESS.md)
>   session-start rules include the don't-drift checklist
> - [OPERATOR-HARNESS.md](./OPERATOR-HARNESS.md) — `verify.py --all`
>   is Objective-A-only; Objective-B tooling is a known gap
>
> **Iterative-by-design.** This doc scaffolds the minimum viable
> discipline. It will evolve: observation schema fields get added,
> templates tighten or expand, anti-drift rules get sharpened as we
> catch ourselves drifting. Each revision is logged at the bottom.

---

## Why this doc exists

Alpha-1 runs two primary objectives simultaneously, and they produce
different evidence:

| Objective | Question being validated | Primary artifacts |
|---|---|---|
| **A — System** | Does YARNNN work as a domain-agnostic operator platform? Do the axioms hold under real use? | ADR seeds, architectural observations, prompt-tweak backlog, UX friction list, primitive-matrix tensions |
| **B — Product** | Does this specific operator (KVK as Simons-trader) actually make money with YARNNN's help? Is the autonomous-agent framework a real edge? | Per-signal realized expectancy, capital trajectory, Reviewer calibration against outcomes, decision-vs-outcome pairs in `decisions.md` |

Without explicit discipline, default drift is toward Objective A — the
engineer-nearest, architecture-adjacent, ADR-producing mode. Objective B
gets paid lip service ("alpha will generate data") but never gets its
own tight reporting loop.

Three failure modes this doc prevents:

1. **Silent Objective-B neglect.** We ship cockpit improvements and prompt tweaks for weeks; the book trends sideways; nobody asked "is the book trending because of YARNNN, despite YARNNN, or orthogonal to YARNNN?"
2. **Conflated observations.** "The cockpit felt slow" gets filed as a UX friction note, but the actual signal was *"I missed a Signal-2 setup because the cockpit took 4s to load"* — an Objective-B friction dressed as Objective-A.
3. **Engineer-default drift inside Objective A.** Within A, we drift toward backend / workflow concerns and miss UX / qualitative-agent-behavior concerns because those are further from the keyboard.

---

## The three-axis observation schema

Every observation note classifies on three axes. If it can't classify on any axis, it isn't an observation — it's a private thought and doesn't belong in `docs/alpha/observations/`.

### Axis 1 — **Objective** (required; may be multi-valued)

- `A-system` — informs whether YARNNN-the-platform works
- `B-product` — informs whether YARNNN-helps-KVK-make-money
- Can be both. Most load-bearing observations are.

### Axis 2 — **Within-A scope** (required if Axis 1 includes A)

Prevents engineer-default drift inside system validation:

- `systematic-workflow` — back-end execution, scheduling, reconciliation, filesystem, primitives, agent pipeline
- `ui-ux` — frontend surfaces, cockpit legibility, navigation, visual friction, operator-facing content clarity
- `qualitative-agent-behavior` — what agents *say*, what YARNNN chooses to surface, how the Reviewer reasons, whether prompts are doing what we think they're doing
- Can be multi-valued. Often a friction spans two of these.

### Axis 3 — **Dimensional classification** (required)

Which FOUNDATIONS v6.0 axiom(s) the observation touches:

- `Substrate` (what persists)
- `Identity` (who acts / authors)
- `Purpose` (why, intent)
- `Trigger` (when invoked)
- `Mechanism` (how — code ↔ LLM judgment spectrum)
- `Channel` (where output addresses)

Multi-valued common.

### Additional metadata (always captured)

- **Severity:** `dead-stop` / `cognitive-load` / `surprise` / `aesthetic`
- **Resolution path:** `prompt-tweak` / `component-patch` / `ADR-candidate` / `persona-identity-edit` / `real-money-observation-only` / `harness-extension`
- **Money impact (B only):** `direct-capital` (affected a real P&L outcome), `decision-impact` (affected my decision quality without yet showing in P&L), `none` (Objective A only)

---

## Observation note template

Every note at `docs/alpha/observations/{YYYY-MM-DD}-{persona}-{slug}.md`:

```markdown
# {YYYY-MM-DD} — {persona} — {one-line summary}

## Classification
- **Objective:** [A-system | B-product | both]
- **Within-A scope:** [systematic-workflow | ui-ux | qualitative-agent-behavior | N/A]
- **FOUNDATIONS dimension:** [Substrate | Identity | Purpose | Trigger | Mechanism | Channel]
- **Severity:** [dead-stop | cognitive-load | surprise | aesthetic]
- **Resolution path:** [prompt-tweak | component-patch | ADR-candidate | persona-identity-edit | real-money-observation-only | harness-extension]
- **Money impact:** [direct-capital | decision-impact | none]

## Context
What was I trying to do? (include persona, mode per CLAUDE-OPERATOR-ACCESS.md)

## What happened
What the cockpit / Reviewer / agent actually did.

## Friction
What was harder, slower, less legible, or surprising than it should be.

## Hypothesis
What change would resolve this? Be specific — file path, prompt section, ADR-candidate-name, or "observe further before acting."

## Counterfactual (Objective B only)
If this observation has money impact: what would have happened without YARNNN? Would I have executed differently, and would that have been better or worse?

## Links
- Proposal ID / decision.md entry / task output / substrate file paths
- Related observations (same-theme cluster)
```

Empty sections are OK — they're informative about which axes an observation touches and which it doesn't.

---

## Dual weekly report templates

Playbook §7.2 previously had a single weekly report template biased toward Objective A. That template is superseded by **two separate reports**, one per objective, both produced Sunday evening.

Both reports read the same underlying substrate (`_performance.md`, `decisions.md`, observation notes, activity log). They differ in framing.

### Objective A report — system-insight framing

Filename: `docs/alpha/reports/week-{N}-{persona}-A-system.md`

Reader: KVK-as-architect + any Claude session starting fresh + future ADR drafting.

```markdown
# Week {N} — {persona} — Objective A (System)
**Range:** {start date} → {end date}

## What worked (keep doing)
- Architectural decisions that held up under real use
- Prompt guidance that produced the right agent behavior
- Cockpit surfaces that were legible without coaching

## What surfaced as friction
Grouped by within-A scope:

### systematic-workflow
- Link observation notes; summarize themes; note frequency

### ui-ux
- Link observation notes; summarize themes; note frequency

### qualitative-agent-behavior
- Link observation notes; summarize themes; note frequency

## ADR candidates this week
- {Candidate} — observation links — FOUNDATIONS dimension — 1x/2x/persona-only categorization

## Prompt-tweak backlog
- Small behavioral changes that don't warrant ADRs but need CHANGELOG entries

## Component-patch backlog
- Small UX or component fixes; severity-ranked

## Phase-transition signal
- Are we on track for Alpha-2? Are friction rates declining?
- Which ADRs would block or enable advancing?

## What remains unverified
Parts of the architecture that *haven't* been stressed this week. Naming them prevents the illusion of coverage.
```

### Objective B report — money-truth framing

Filename: `docs/alpha/reports/week-{N}-{persona}-B-product.md`

Reader: KVK-as-trader now + KVK-as-trader-future-self reviewing whether Alpha-2 live-money is warranted. Dual-audience tone: honest with self + evidence for hypothesis evaluation.

```markdown
# Week {N} — {persona} — Objective B (Product)
**Range:** {start date} → {end date}
**Starting equity:** ${X}
**Ending equity:** ${Y} (change: ${Y-X}, {%})

## This week's capital trajectory
- Week P&L (realized + unrealized)
- Rolling 30-day P&L
- Drawdown from rolling high
- Against declared success criteria (`_operator_profile.md` success block)

## Per-signal attribution
Reads `_performance.md` by_signal block. Per signal:

| Signal | Trades this week | Realized P&L | Expectancy (R) | Recent-20 vs declared baseline | State |

Flag any signal whose recent-20-trade expectancy has turned negative (decay-guardrail candidate).

## Reviewer calibration
For AI Reviewer verdicts that resolved to outcomes this week:
- Approve verdicts → realized P&L sign + R-multiple
- Reject verdicts → did the rejected proposal, if executed, have been a gain or loss? (counterfactual where knowable)
- Defer verdicts → did human judgment approve/reject, and how did that resolve?

Per-verdict table:
| Proposal | Verdict | Reviewer reasoning | Outcome | Verdict-outcome alignment |

## Decisions made this week (Claude + KVK)
From `decisions.md` tail:
- Approvals
- Rejections (mine and Reviewer's)
- Escalations that required KVK (how many; did they resolve in time?)
- Time-to-decision on time-sensitive proposals

## Honesty check (the most important section — do not skip)
Questions every week, answered directly:
1. **Did the book grow because of YARNNN, despite YARNNN, or orthogonal to YARNNN?**
2. **Without YARNNN, what would I have done differently this week?** Better or worse outcome?
3. **Did I override any Reviewer rejection? What happened?**
4. **Did I take any trade without signal attribution?** (Should be zero. If not, this is character drift.)
5. **Is my current `_risk.md` too loose, too tight, or calibrated?**

## Hypothesis status
Operator hypothesis is in `_operator_profile.md`: *"Discipline in signal execution, position-sizing math, and signal retirement. My edge compounds through consistent sizing, diversification, signal retirement, never overriding the model."*

- Is this week's evidence consistent with the hypothesis?
- Is the evidence strong enough to update conviction up, down, or same?
- If same: what evidence would be needed to update?

## Decision impact (forward-looking)
- Any Alpha-2 readiness signal? (Per playbook §8 phase-transition criteria)
- Any signal that should be retired / retuned at next quarterly audit?
- Any capital-allocation change warranted?
```

### Both reports produced together, even when one is thin

Early alpha weeks will have thin Objective B reports (few trades → little data). Produce them anyway — the absence is informative. A week of zero trades with the Simons-persona might be character-correct (patient discipline) or might be a substrate problem (signal detection misfiring). Discipline shows when we write the thin report honestly rather than skipping it.

---

## Session-start don't-drift checklist

Every Claude session touching the alpha asks three questions before substantive work:

1. **Are we operating for system insight, money-truth, or both this session?** Name it. If unclear, ask KVK.
2. **What UX friction might a non-engineer operator feel in what we're about to do?** Answer even if "none obvious." Forcing the question surfaces the gaps.
3. **What did / will this session move on the money-truth side, even if the answer is nothing?** "Nothing, I'm on architecture today" is a valid answer; it's not valid to skip asking.

This checklist lives in CLAUDE-OPERATOR-ACCESS.md "rules of thumb" (cross-referenced back here).

---

## Anti-drift rules

Rules that catch the specific failure modes we know we'll drift toward.

### R1 — Observations without any axis tagged are not observations

If a note can't classify Objective, Within-A scope, or dimension, it's a private thought or a todo item. Route it to the right place:
- Private thought → keep in your head or write a scratch note outside `docs/alpha/`
- Todo item → `TodoWrite` tool, or a file in a todo repo, not here
- Genuine observation → force classification; if forced, you'll notice what axis it actually occupies

### R2 — "Cockpit slow" is incomplete; "Cockpit slow AND I missed a trade" is complete

Speed / usability / aesthetic frictions get upgraded to money-truth friction if they affected a decision. Always ask the money-impact question on UX observations.

### R3 — If the weekly Objective B report is thin, the week was thin — write it anyway

Never combine weekly reports to mask sparse B data. Writing "Week 2, zero trades fired, one Reviewer defer, counterfactual unknown" is more valuable than burying the silence.

### R4 — When architecture work directly helps one objective, name which

"Prompt tweak for Reviewer reasoning" might be pure Objective A (better reviewer behavior) or Objective B (prevents a real decision error). If the tweak is in response to a specific observation, tag which objective the observation came from.

### R5 — Iterative scaffold is a feature

This doc's schema, templates, and anti-drift rules will evolve. We'll find new axes we need to capture (e.g., "timezone friction" if Korea↔LA operation surfaces it). Extend rather than replace. Revision history at bottom tracks evolution.

---

## Iterative evolution — how this doc grows

When to amend:

- **New observation pattern keeps slipping** through current schema → add an axis or metadata field
- **Weekly report keeps missing a critical question** → amend the template
- **New anti-drift failure mode observed** → add an R-rule
- **New objective emerges** (e.g., commerce adds Objective C in Alpha-1.5, or GTM validation becomes its own objective) → extend the objective list + add a report template

When to NOT amend:

- Single-week anecdote — wait for a second instance before codifying
- Personal preference about report tone — the templates are a floor, not a ceiling; embellish within an instance, don't rewrite the template

---

## Readings this doc inherits from

- `ALPHA-1-PLAYBOOK.md` §2 governance, §6 anti-discretion ladder, §7 friction-capture loop, §8 phase transitions
- `CLAUDE-OPERATOR-ACCESS.md` three-mode access + discretion ceiling
- `OPERATOR-HARNESS.md` verify/connect/reset commands
- `personas.yaml` persona registry
- FOUNDATIONS v6.0 six-dimensional axiom model

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-21 | v1 — Initial. Two objectives (A-system, B-product) named. Three-axis observation schema (Objective / Within-A scope / FOUNDATIONS dimension) + severity + resolution path + money impact. Dual weekly report templates replacing playbook §7.2 single-template. Session-start don't-drift checklist. Five anti-drift rules (R1–R5). Iterative-evolution protocol. |
