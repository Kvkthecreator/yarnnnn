# Output Quality First Principles — Multi-Agent vs. Single-Agent Ceiling

> **Date**: 2026-03-29
> **Context**: E2E quality testing revealed that multi-step processes produce output indistinguishable from single-agent output. This analysis explores why, and what the right trajectory is.

---

## The Finding

E2E test results (2026-03-29, post-quality-hardening):
- **competitive-intel-brief** (2-step: research→content): Step 1 = 674 words. Step 2 = 23 words (failed — tool budget consumed by chart attempts). When step 2 worked, it produced 285 words — shorter than step 1.
- **stakeholder-update** (2-step: research→content): Step 1 = 540 words. Step 2 = 683 words (passed, but plain markdown).

A single Claude prompt asking for a competitive intelligence brief produces 2000-3000 words with charts, diagrams, and structured analysis. Our 2-step process produced less.

## Why Multi-Step Underperforms Single-Shot (Today)

### 1. The handoff destroys reasoning context
When research-agent produces 674 words and content-agent receives it as "Prior Step Output," the content-agent has NO access to the web search results, the reasoning chain, the sources evaluated and rejected, the confidence levels. It receives finished prose, not the thinking behind it.

A single agent that researches AND composes retains all reasoning context. It knows WHY it rated a competitor as high-threat, so it can emphasize that in the executive summary. The compose step only sees the final text.

### 2. We split "think" from "write" — but the model does both
The research→content split assumes investigation and composition are different skills requiring different agents. But Claude Sonnet is equally capable at both. Splitting them means:
- Two context windows instead of one (double the context-gathering cost)
- Two prompt assemblies (double the methodology/instruction overhead)
- A lossy handoff in between (information compression)

### 3. Tool budget splits across steps
With 3 tool rounds per step, the research agent gets 3 rounds for web search, and the content agent gets 3 rounds for chart generation. A single agent with 6 rounds can allocate dynamically — 4 for research, 2 for charts — based on what it finds.

### 4. Output ambition was calibrated too low
Process instructions said "minimum 500 words" when professional deliverables are 2000-5000 words. The multi-step process didn't produce shorter output because of the architecture — it produced shorter output because we asked for less.

## When Multi-Agent Actually Adds Value

Multi-agent coordination adds value in three specific cases:

### A. Different tool access
CRM agent has platform relationship data. Research agent has web search. Neither has both. A meeting-prep-brief genuinely needs both: CRM provides "last interaction with Alice was March 15, discussed Q4 proposal" and research provides "Alice's company just raised Series B."

### B. Context window economics (at scale)
When a user has 50 Slack channels, 200 Notion pages, and 30 prior outputs, one agent can't hold everything. A sub-agent pattern (like Claude Code's) delegates focused sub-tasks: "summarize #engineering channel this week" → returns 200-word summary → parent agent composes the full digest.

This becomes relevant at scale, not on day 1.

### C. Accumulated domain memory
After 20 runs, a research agent's workspace has accumulated competitive intelligence that a content agent's workspace doesn't. The research agent's `memory/observations.md` contains "Competitor X shifted to enterprise pricing in January — watch for follow-on moves." This accumulated memory IS the differentiation — but it accrues over months, not at task creation.

## The Trajectory

```
Phase 0 (now):     Single-agent, higher ambition
                   Most task types → 1 step, 1 agent
                   Raise output target to 2000-3000 words
                   Increase tool rounds to 5-6
                   Multi-step only where tool access genuinely differs

Phase 1 (month 1-3): Accumulated memory creates real differentiation
                   Research agent's 20th brief > its 1st
                   Domain knowledge compounds across runs
                   Multi-agent value emerges bottom-up through tenure

Phase 2 (month 3+): Context economics force sub-agent delegation
                   Context windows fill with accumulated state
                   Sub-delegation becomes performance optimization
                   Artifact model (ADR-148) becomes structurally necessary
```

## Right-Sized Process Definitions

| Task Type | Current | Recommended | Why |
|-----------|---------|-------------|-----|
| competitive-intel-brief | 2 (research→content) | **1** (research) | Research agent has web_search + chart + mermaid + compose_html |
| market-research-report | 2 (research→content) | **1** (research) | Same capabilities, one context window retains reasoning |
| industry-signal-monitor | 2 (marketing→research) | **1** (marketing) | Marketing agent has web_search, can investigate signals |
| due-diligence-summary | 2 (research→content) | **1** (research) | Deep investigation + formatted output in one pass |
| meeting-prep-brief | 2 (crm→research) | **2** (crm→research) | CRM has platform data, research has web search — genuinely different |
| stakeholder-update | 2 (research→content) | **1** (content) | Content agent reads workspace context + formats |
| relationship-health-digest | 2 (slack_bot→crm) | **2** (slack_bot→crm) | Slack bot has platform read, CRM has relationship domain |
| project-status-report | 3 (slack_bot→crm→content) | **2** (slack_bot→content) | Slack extraction + formatted report (CRM step adds little) |
| slack-recap | 1 (slack_bot) | **1** (slack_bot) | Already single-step |
| notion-sync-report | 1 (notion_bot) | **1** (notion_bot) | Already single-step |
| content-brief | 2 (research→content) | **1** (research) | Research + write in one context window |
| launch-material | 2 (marketing→content) | **1** (marketing) | Marketing positioning + formatted output in one pass |
| gtm-tracker | 2 (marketing→content) | **1** (marketing) | Marketing intelligence + formatted tracker in one pass |

Result: 13 task types go from 22 total steps → **15 total steps**. Multi-step shrinks from 10 types to 3.

## Relationship to ADR-148

ADR-148 (Output Artifact Architecture) describes the right end-state for Phase 2 — when context economics and accumulated memory make multi-agent coordination structurally necessary. At that point, artifact-aware composition, named artifact types, and layout templates become valuable infrastructure.

For Phase 0, the simpler model (one agent, one output.md, existing compose service) is correct. The architecture should evolve toward ADR-148 as the product matures, not implement it upfront.

## Key Insight

The multi-agent architecture isn't wrong — the **timing** of its value realization is. Agents earn their differentiation through accumulated memory over months, not through type labels at creation. The architecture should support that trajectory:

1. Agents exist and accumulate memory (already true)
2. Single-agent execution for most task types (Phase 0 change)
3. Multi-agent only where tool access requires it (Phase 0 change)
4. Artifact model when context economics demand it (Phase 2, ADR-148)

This aligns with FOUNDATIONS Axiom 3 (agents develop inward — knowledge depth, not capability breadth) and Axiom 4 (value comes from accumulated attention — tenure, not labels).
