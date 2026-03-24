# Cost Model — Per-Project Economics

> **Status**: Canonical
> **Date**: 2026-03-24
> **Related**: ADR-100 (tier model), ADR-130 (capabilities), ADR-136 (charter architecture)

---

## Per-Project Cost Breakdown

With cadence enforcement (ADR-136) and PM prompt modes, each project's cost is predictable.

### Weekly Project (1 contributor + PM)

| Step | Model | Calls/Week | Cost/Call | Weekly |
|------|-------|-----------|----------|--------|
| Contributor pre-screen (Tier 2) | Haiku | 1 | $0.001 | $0.001 |
| Contributor generation | Sonnet | 1 | $0.03-0.05 | $0.04 |
| PM coordination pulses (Tier 3) | Haiku | 2-4 | $0.001 | $0.003 |
| PM assembly + delivery | Sonnet | 1 | $0.05 | $0.05 |
| PM quality evaluation | Haiku | 1 | $0.001 | $0.001 |
| Compose (render service) | Internal | 1 | ~$0 | $0 |
| **Total** | | | | **~$0.10/week** |

**Monthly: ~$0.40-0.50 per project**

### Weekly Project (3 contributors + PM)

| Step | Model | Calls/Week | Cost/Call | Weekly |
|------|-------|-----------|----------|--------|
| 3× Contributor pre-screen | Haiku | 3 | $0.001 | $0.003 |
| 2× Contributor generation (1 skips — no change) | Sonnet | 2 | $0.04 | $0.08 |
| PM coordination | Haiku | 4 | $0.001 | $0.004 |
| PM assembly | Sonnet | 1 | $0.05 | $0.05 |
| PM evaluation + reflection | Haiku + Sonnet | 2 | $0.015 | $0.03 |
| **Total** | | | | **~$0.17/week** |

**Monthly: ~$0.70 per project**

### Daily Project (briefer + PM — Slack recap)

| Step | Model | Calls/Week | Cost/Call | Weekly |
|------|-------|-----------|----------|--------|
| 5× Briefer pre-screen (weekdays) | Haiku | 5 | $0.001 | $0.005 |
| 5× Briefer generation | Sonnet | 5 | $0.03 | $0.15 |
| 5× PM passthrough delivery | Haiku | 5 | $0.001 | $0.005 |
| **Total** | | | | **~$0.16/week** |

**Monthly: ~$0.65 per project**

---

## Cost Optimization Levers

### Implemented

1. **Cadence enforcement (ADR-136)** — agents only run when cadence window opens. Weekly = 1 run/week, not unbounded.
2. **30-min cooldown (Tier 1)** — prevents cascade loops.
3. **Tier 2 pre-screen (Haiku, 2 tool rounds)** — cheap check before expensive generation. Skips if nothing changed.
4. **PM prompt modes** — Haiku for coordination, Sonnet only for composition + reflection.

### Future Optimizations

5. **Output diffing** — if contributor output is <10% different from last run, skip delivery. Saves assembly Sonnet call.
6. **Shared context cache** — multiple agents in same project don't re-read the same workspace files.
7. **Prompt caching** — Anthropic prompt caching for stable system prompts (PM template, role prompts).
8. **Haiku-only projects** — simple briefer projects could use Haiku for generation (cheaper, lower quality).

---

## Pricing Tiers (Updated)

| Plan | Projects | Agents | Monthly LLM Cost | Suggested Price | Gross Margin |
|------|----------|--------|------------------|-----------------|-------------|
| **Free** | 2 | 3-4 | ~$1.00 | $0 | -100% (trial) |
| **Pro** | 10 | 15-20 | ~$6.00 | $19/mo | 68% |
| **Business** | 50 | 75-100 | ~$30.00 | $99/mo | 70% |

### Comparison with ADR-100 (old model)

| Metric | ADR-100 (old) | Current (ADR-136) |
|--------|---------------|-------------------|
| Primary gate | Monthly messages (50/∞) | Projects + cadence |
| Cost driver | Unpredictable (user msg volume) | Predictable (N projects × cadence) |
| Agent limit | 2 free / 10 pro | Same |
| Execution model | Unbounded pulses | Cadence-bounded |
| Cost per project | Unknown (varied by usage) | ~$0.50/month |

### Key Insight

**The cost is now per-project, not per-message.** A user with 5 weekly projects costs ~$2.50/month regardless of how much they chat (chat is user-initiated, not agent-generated). This makes the business model predictable:

- **CAC recovery**: Pro user ($19/mo) at $6/mo cost = $13/mo contribution margin
- **Break-even**: ~1 month for direct costs
- **LTV at 12-month retention**: $156 contribution / $72 cost = 2.2x

---

## Token Optimization Strategy

### Current Token Usage per Sonnet Call

| Component | Tokens | Source |
|-----------|--------|--------|
| System prompt (PM) | ~2000 | PM prompt template + project context |
| System prompt (contributor) | ~3000 | Role prompt + workspace context + SKILL.md |
| Input context (platform content) | ~5000-10000 | Platform sync data |
| Tool results | ~2000-5000 | Search/Read results per tool round |
| Output | ~500-2000 | Generated content |
| **Total per call** | **~12000-20000** | |

### Optimization Opportunities

1. **System prompt caching**: PM and contributor prompts are mostly stable. Anthropic's prompt caching could reduce input token cost by 90% for the stable portion.
2. **Context window management**: cap platform content injection to most-recent N items (currently unbounded).
3. **SKILL.md selective injection**: only inject SKILL.md for capabilities the agent's type has (already done via `has_asset_capabilities()`).
4. **Workspace read caching**: within a single pulse cycle, cache workspace file reads.
