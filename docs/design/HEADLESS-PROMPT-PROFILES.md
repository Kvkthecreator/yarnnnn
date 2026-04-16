# Investigation: Headless Prompt Profiles

**Status:** Draft — investigation for future ADR
**Date:** 2026-04-16
**Context:** ADR-186 (TP Prompt Profiles) introduced surface-aware behavioral assembly for conversational mode. This doc investigates whether the same pattern applies to headless (task pipeline) execution.
**Related:** ADR-141 (Unified Execution), ADR-166 (Registry Coherence — output_kind), ADR-173 (Accumulation-First), ADR-182 (Pre-Gather Pipeline Optimization)

---

## Question

Does `build_task_execution_prompt()` in `task_pipeline.py` benefit from output_kind-aware prompt profiles, analogous to ADR-186's surface-aware profiles for conversational mode?

---

## Current State

`build_task_execution_prompt()` (task_pipeline.py:1458) builds a single monolithic system prompt for all headless task executions. It includes:

1. **Output rules** (~100 tokens) — concise, professional, no emojis
2. **User context** (variable) — identity, prefs, brand from `_load_user_context()`
3. **Agent instructions** (variable) — from AGENT.md
4. **Methodology index** (~150 tokens) — playbook file references (ADR-130)
5. **Workspace conventions** (~200 tokens) — file paths, write modes
6. **Accumulation-first execution** (~400 tokens) — gap-only generation philosophy
7. **Tool usage (headless)** (~500 tokens) — decision order, WebSearch principles, stopping criteria
8. **Visual assets** (~300 tokens) — RuntimeDispatch guidance, hero image patterns
9. **Empty context handling** (~50 tokens)
10. **DELIVERABLE.md spec** (variable) — quality contract
11. **Reflection postamble** (~200 tokens) — self-assessment extraction

Total static: ~1,900 tokens + variable sections. This is already much leaner than the conversational prompt (~10K pre-ADR-186), because headless was purpose-built for task execution.

### The output_kind axis

ADR-166 established four output kinds:

| output_kind | Shape | Agent behavior | Current prompt relevance |
|---|---|---|---|
| `accumulates_context` | Write to `/workspace/context/` domains, entity profiles, signals | Research, discover, organize knowledge. Full tool surface (3-5 rounds). | Needs workspace conventions, tool usage, WebSearch guidance. Does NOT need visual assets section. |
| `produces_deliverable` | Produce polished output (report, brief, deck) | Compose from gathered context. Reduced tool surface (0-1 rounds, ADR-182). | Needs visual assets, DELIVERABLE.md spec, generation brief. Does NOT need WebSearch guidance (context pre-gathered). |
| `external_action` | Write to external platform (Slack post, Notion update) | Read context, compose, post via platform tool. | Needs platform tool guidance. Does NOT need workspace conventions, visual assets, or accumulation-first. |
| `system_maintenance` | Run deterministic Python executor | Back-office task. No LLM. | Does NOT use `build_task_execution_prompt()` at all — goes through `_execute_tp_task()`. |

### Where the monolith hurts

For `produces_deliverable` tasks (the most expensive to run), the prompt includes ~500 tokens of WebSearch guidance and ~200 tokens of workspace conventions that are irrelevant — ADR-182 already reduces tool surface to `WriteFile` + `RuntimeDispatch` only. The agent reads these sections, processes them as context, and ignores them.

For `accumulates_context` tasks, the ~300 tokens of visual asset guidance and the DELIVERABLE.md spec are irrelevant — these agents write entity profiles and signal logs, not hero images and charts.

### Estimated waste

| output_kind | Irrelevant sections | ~Tokens wasted | Runs/month (typical) | Monthly waste |
|---|---|---|---|---|
| `accumulates_context` | Visual assets, DELIVERABLE.md | ~400 | 60-120 | 24K-48K input tokens |
| `produces_deliverable` | WebSearch guidance, workspace conventions | ~700 | 20-40 | 14K-28K input tokens |
| `external_action` | Visual assets, workspace conventions, accumulation-first | ~900 | 5-10 | 4.5K-9K input tokens |

**Total estimated monthly waste: ~42K-85K input tokens**, or **~$0.13-0.26/month** at Sonnet $3/MTok. This is not significant enough to be a cost optimization priority.

---

## Assessment

### Why this is lower priority than ADR-186

1. **The headless prompt is already lean** (~1,900 tokens static). The conversational prompt was ~10K tokens of behavioral noise. There's much less fat to cut.

2. **Headless runs once per task, not per message.** The conversational prompt is injected on every chat turn (potentially 10-20 turns per session). The headless prompt is injected once. The token savings per unit of work are much smaller.

3. **ADR-182 already addressed the main cost lever.** Pre-gather pipeline optimization reduced `produces_deliverable` from ~90K cumulative input tokens to ~18K by cutting tool rounds from 3-5 to 0-1. That saved ~$0.22/task. Profile-based prompt trimming would save ~$0.002/task. Two orders of magnitude less.

4. **Risk of behavioral regression is higher.** The headless prompt is less tested (no interactive feedback loop — output is evaluated asynchronously). A prompt change that subtly degrades output quality wouldn't be caught until the next user review. The conversational prompt has immediate feedback (user responds).

### When this becomes worth doing

- When the number of monthly task executions exceeds ~10K (cost crosses ~$3/month in waste)
- When a new output_kind is added that has fundamentally different behavioral needs
- When headless prompt debugging becomes a maintenance problem (currently it's one file, one function, straightforward)

### If we did it, what would it look like

Three profiles, keyed on `output_kind`:

```python
HEADLESS_PROFILES = {
    "accumulates_context": "accumulate",
    "produces_deliverable": "produce",
    "external_action": "act",
    # system_maintenance: no prompt — uses _execute_tp_task()
}
```

**`accumulate` profile:** Output rules + user context + agent instructions + methodology + workspace conventions + tool usage (full) + accumulation-first + reflection postamble. No visual assets, no DELIVERABLE.md.

**`produce` profile:** Output rules + user context + agent instructions + methodology + visual assets + DELIVERABLE.md + generation brief + reflection postamble. No WebSearch guidance, no workspace conventions (not writing to context domains).

**`act` profile:** Output rules + user context + agent instructions + platform tool guidance. Minimal prompt — read context, compose, post.

---

## Recommendation

**Park this.** The savings are not material ($0.13-0.26/month), the risk is real (behavioral regression without interactive feedback), and the current prompt is already lean. Revisit when:
- Monthly task executions exceed 10K
- A new output_kind is added
- The headless prompt grows beyond ~3K tokens static

Add a reevaluation trigger to the ADR-186 "Future considerations" section rather than creating a separate ADR now.
