# Evaluation Framework: TP Prompt Profiles (ADR-186)

**Status:** Draft — methodology for future evaluation
**Date:** 2026-04-16
**Context:** ADR-186 introduced workspace/entity prompt profiles. This doc defines how to evaluate whether the profiles improve TP judgment quality.
**Related:** ADR-186 (TP Prompt Profiles), ADR-162 (Inference Hardening — eval harness precedent), docs/architecture/TP-DESIGN-PRINCIPLES.md

---

## What We Want to Know

**Primary question:** Does the entity profile produce better TP judgment for entity-scoped interactions compared to the pre-ADR-186 monolith?

**Secondary question:** Does the workspace profile maintain equivalent or better quality for workspace-wide interactions?

"Better judgment" means:
1. **Feedback routing accuracy** — TP routes user corrections to the correct layer (domain / agent / task) more often
2. **First-try action success** — TP takes the right action on the first tool call, without needing clarification or retry
3. **Response relevance** — TP's text responses reference the scoped entity's specific context, not generic guidance
4. **Behavioral compliance** — TP follows entity-specific protocols (feedback communication, temporal model, act + record) consistently

---

## Evaluation Methods

### Method 1: Log-Based Analysis (Passive, Zero Cost)

**What:** Analyze the `[TP:PROFILE]` log lines and associated tool call patterns from production.

**Setup:** The logging already exists (`resolve_profile()` in `chat.py` logs `[TP:PROFILE] surface=X → profile=Y` on every chat message). Extend with:

```python
# In chat.py, after tool execution:
logger.info(f"[TP:TOOL] profile={profile} tool={tool_name} success={result.get('success')}")
```

**Metrics derivable from logs:**

| Metric | How to compute | Good signal |
|---|---|---|
| Tool call distribution per profile | Count tool calls by name, grouped by profile | Entity profile should show higher ManageTask(evaluate/steer) and UpdateContext(agent/task) rates than workspace |
| First-tool-call accuracy | % of turns where the first tool call succeeds | Should be ≥ current baseline (or increase) |
| Tool round count | Average number of tool rounds per message | Entity profile should have fewer rounds (less hunting) |
| Clarify rate | % of turns that use Clarify primitive | Entity profile should have lower Clarify rate (scoped context reduces ambiguity) |

**When to run:** After 2 weeks of production usage with both profiles active. Need ≥50 entity-profile sessions and ≥100 workspace-profile sessions for statistical relevance.

**Cost:** Zero incremental (log analysis only).

### Method 2: Feedback Routing Accuracy (Targeted, Low Cost)

**What:** Test TP's ability to route user feedback to the correct target across both profiles.

**Setup:** A set of 20 user feedback messages with known correct routing. Run each through both profiles (with appropriate surface context) and score routing accuracy.

**Test fixture format:**

```python
FEEDBACK_ROUTING_TESTS = [
    {
        "message": "use formal tone in all reports",
        "surface": {"type": "task-detail", "taskSlug": "competitive-brief"},
        "expected_tool": "UpdateContext",
        "expected_target": "agent",  # Cross-task style preference
        "expected_profile": "entity",
    },
    {
        "message": "focus on pricing next week",
        "surface": {"type": "task-detail", "taskSlug": "competitive-brief"},
        "expected_tool": "UpdateContext",
        "expected_target": "task",
        "expected_feedback_target": "criteria",
        "expected_profile": "entity",
    },
    {
        "message": "stop tracking Tabnine",
        "surface": {"type": "task-detail", "taskSlug": "track-competitors"},
        "expected_tool": "ManageDomains",
        "expected_action": "remove",
        "expected_profile": "entity",
    },
    {
        "message": "set up a weekly report on market trends",
        "surface": {"type": "idle"},
        "expected_tool": "ManageTask",
        "expected_action": "create",
        "expected_profile": "workspace",
    },
    # ... 16 more test cases covering edge cases
]
```

**Scoring:**
- **Correct tool** (40%): did TP call the right primitive?
- **Correct target/action** (40%): did it use the right target (for UpdateContext) or action (for ManageTask/ManageDomains)?
- **Correct communication** (20%): did it follow the feedback communication protocol (confirm + timing + offer rerun)?

**How to run:** Can be run offline with a mock `execute_primitive` that returns success. Uses Claude API directly with the assembled system prompt. Cost: ~20 API calls × ~15K tokens = ~$1 per run.

**Baseline:** Run the same test cases against the old monolithic prompt to establish a baseline score before comparing against profiles.

### Method 3: Paired Comparison (Manual, High Signal)

**What:** For 10 real user interactions, compare the entity profile response against what the monolithic prompt would have produced.

**Setup:** When Kevin is on a task page giving feedback, capture:
1. The user message
2. The entity profile response (production)
3. A shadow response from the monolithic prompt (offline replay, same context)

**Scoring criteria (per interaction, 1-5 scale):**

| Criterion | 1 (poor) | 3 (adequate) | 5 (excellent) |
|---|---|---|---|
| **Relevance** | References generic guidance unrelated to task | Addresses the task but with generic framing | Directly addresses this task's specific context |
| **Action accuracy** | Wrong tool or wrong target | Right tool, wrong parameter | Right tool, right target, right parameters |
| **Response efficiency** | Multiple clarification rounds needed | One unnecessary clarification | Correct action on first attempt |
| **Protocol compliance** | No feedback communication protocol | Partial (confirms but no timing) | Full (confirm + timing + offer rerun) |

**When to run:** After 1 week of production usage. Kevin grades each interaction. 10 paired comparisons is sufficient for a directional signal.

**Cost:** ~$0.50 in shadow API calls + 30 minutes of manual grading.

---

## Success Criteria

| Metric | Baseline (monolith) | Target (entity profile) | Measurement |
|---|---|---|---|
| Feedback routing accuracy | TBD (establish with Method 2) | ≥90% correct tool + target | Method 2 |
| First-try action success | TBD (establish from logs) | ≥ baseline or +10% | Method 1 |
| Average tool rounds (entity) | TBD | ≤ baseline | Method 1 |
| Paired comparison score | N/A | ≥ 4.0 / 5.0 average | Method 3 |

**Workspace profile success:** Workspace profile scores should be ≥ monolith baseline on all metrics (no regression).

---

## Failure Modes to Watch

1. **Profile boundary surprise.** User on task page says "create a new task" — entity profile doesn't include creation guidance. Watch for: TP failing to create tasks from entity-scoped surfaces. **Mitigation:** ManageTask(action="create") is in the tool set regardless; creation just lacks catalog guidance. Monitor Clarify rate on entity profile for "what type?" clarifications.

2. **Workspace profile too noisy for experienced users.** The full catalog is always injected even for users who've been using the system for weeks. **Signal:** Workspace profile Clarify rate stays high even for users with rich workspace_state. **Mitigation:** Future work could add a "mature workspace" variant that drops onboarding guidance.

3. **Entity compact index too lean.** The scoped index shows only this entity's state. If TP needs cross-entity awareness (e.g., "this task reads from competitors domain which is empty"), it might miss it. **Signal:** TP fails to flag context gaps that the workspace index would have surfaced. **Mitigation:** Entity index already includes domain health; add entity-specific domain-to-task mapping if needed.

---

## Implementation Sequence

1. **Week 0:** Production deployment (already done — ADR-186 committed)
2. **Week 1:** Method 1 setup — add `[TP:TOOL]` log line to chat.py
3. **Week 1-2:** Method 3 — Kevin grades 10 paired comparisons during normal use
4. **Week 2:** Method 2 — build feedback routing test fixtures, establish baseline, run against profiles
5. **Week 3:** Analyze all three methods, decide on adjustments

**Total cost:** ~$1.50 in API calls + 30 minutes manual grading + log analysis time.

---

## Non-Goals

- **A/B testing infrastructure.** With one user (Kevin), A/B testing is not statistically meaningful. Paired comparison (Method 3) gives the same signal with less infrastructure.
- **Automated quality scoring.** LLM-as-judge for prompt quality is circular (Claude evaluating Claude's prompt). Manual grading is more trustworthy at this scale.
- **Headless evaluation.** Task pipeline prompt profiles are a separate investigation (see `docs/design/HEADLESS-PROMPT-PROFILES.md`). This framework evaluates conversational profiles only.
