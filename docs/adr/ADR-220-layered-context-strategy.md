# ADR-220: Layered Context Strategy — Filesystem-Native Narrative Rollup + In-Session Compaction Sunset

> **Status**: Implemented (2026-04-26 — Commits A + B + C all landed in branch `claude/adr-220-context-strategy`).
> **Date**: 2026-04-26
> **Authors**: KVK, Claude
> **Dimensional classification**: **Mechanism** (Axiom 5 — how prompt context is assembled) primary, **Substrate** (Axiom 1 — `recent.md` as filesystem-native rollup) secondary, **Channel** (Axiom 6 — Claude API channel discipline) tertiary.
> **Extends**: [ADR-159](./ADR-159-filesystem-as-memory.md) (Filesystem-as-Memory), [ADR-186](./ADR-186-tp-prompt-profiles.md) (Prompt Profiles), [ADR-209](./ADR-209-authored-substrate.md) (Authored Substrate signal), [ADR-219](./ADR-219-invocation-narrative-implementation.md) (Invocation + Narrative).
> **Supersedes**: [ADR-067](./ADR-067-session-compaction-architecture.md) Phase 3 in-session LLM compaction (`maybe_compact_history` + `COMPACTION_THRESHOLD` deleted).

---

## Context

ADR-219 widened `session_messages.role` to six Identity classes (user, assistant, system, reviewer, agent, external — migration 161). It made `/chat` the universal narrative surface — every invocation in the workspace lands as a chat-shaped entry, with weight-driven UI density.

That widening exposed two latent issues in the Claude API prompt-assembly path that pre-dated ADR-219 but only became active after Commit 2 of ADR-219 landed:

1. **Bug — non-conversation roles leaked to Claude's API.** `build_history_for_claude()` passed `role` straight through; Claude's API only accepts `user` and `assistant`. A reviewer verdict, system card, agent task completion, or external MCP entry in the last-10-message window would crash the chat turn with an Anthropic API "invalid role" error.

2. **Cost trap — tool history bloat on older assistant turns.** Every windowed assistant turn re-injected its full `tool_use`/`tool_result` blocks on every subsequent turn. Tool-heavy multi-turn sessions accumulated 3-5K tokens per past tool call. In-session LLM compaction (`maybe_compact_history`) only kicked in at 40K tokens — far above where most operator workflows live.

Beyond fixing the two issues, ADR-219 raised a deeper architectural question: **how should non-conversation invocations re-enter YARNNN's reasoning?** Reviewer verdicts, agent task completions, MCP foreign-LLM writes — these are real workspace events that YARNNN should reason about, but they're not chat turns.

ADR-159 already established the filesystem-as-memory model: filesystem-native rollups (`/workspace/memory/conversation.md`) replace LLM-summarization. ADR-209 already provides a substrate-side authorship signal (`workspace_file_versions`) surfaced in the compact index as a one-liner. ADR-220 completes the model with the narrative-side equivalent.

---

## Decision

### Three-layer context model

Every YARNNN chat turn assembles its prompt from three layers, each with a clear ownership boundary:

| Layer | Source | Cached? | Token budget | Identity-handling |
|---|---|---|---|---|
| **Layer 1 — Static** | `BASE` + behavioral profile (workspace/entity per ADR-186) + `TOOLS_CORE` + `PLATFORMS` + `CONTEXT_AWARENESS` | Yes (cache_control: ephemeral) | ~12-15K, ~95% cache hit | n/a — no per-turn variance |
| **Layer 2 — Workspace state** | `format_compact_index()` + two complementary one-liner pointers | No (changes per turn) | 600-token ceiling | Per-Identity authorship one-liner (ADR-209); narrative events one-liner (this ADR) |
| **Layer 3 — Conversation history** | `build_history_for_claude(messages)` over the windowed `session_messages` | Partial | ~2-3K (10-message window) | **Filtered to user/assistant only** (Commit A) |

### Two complementary signals in Layer 2

The compact index gets **two one-liner pointers**, each ~30 tokens, both pointing at filesystem-native files for on-demand detail:

**Substrate axis (existing — ADR-209):**
```
Recent activity (24h, 23 revisions): operator (3), yarnnn (12), agent (5), system (3) — use ListRevisions/ReadRevision/DiffRevisions to inspect.
```
Answers: "who wrote what file" — file-level mutation truth from `workspace_file_versions`.

**Narrative axis (new — this ADR):**
```
Recent events (7 in 24h): 3 reviewer verdicts, 2 task deliveries, 1 MCP write, 1 digest — read /workspace/memory/recent.md if needed.
```
Answers: "what invocations happened" — invocation-level activity from `session_messages`, filtered to material weight + non-conversation Identity classes.

The two layers don't duplicate. Substrate authorship is the *file-system* fact; narrative is the *operator-facing log*. Most invocations produce substrate mutations, but not all (e.g., `pull_context` MCP read), and some substrate mutations don't have a narrative entry (e.g., backfill migrations). They are orthogonal axes of the same workspace.

### `/workspace/memory/recent.md` is the narrative-side rollup

A new workspace file written by the existing `back-office-narrative-digest` task (ADR-219 Commit 3). The digest's executor gains one additional output: alongside the rolled-up chat entry it already writes, it composes `recent.md` with a curated 24h roll-up of material-weight non-conversation entries.

Format:

```markdown
# Recent workspace events
Last updated: 2026-04-26 14:30 UTC · 24h window

## Reviewer verdicts (4)
- 2h ago — APPROVE: order-amzn-1k-shares (proposal-abc123)
- 5h ago — REJECT: discount-launch-50pct (proposal-def456) — outside risk envelope
- 1d ago — APPROVE: weekly-report-send (proposal-ghi789)
- 1d ago — DEFER: order-tsla-500 — needs clarification

## Agent task completions (2)
- 4h ago — competitor-tracker delivered scan → /tasks/competitor-scan/outputs/2026-04-26/
- 1d ago — revenue-report delivered weekly → /tasks/revenue-report/outputs/2026-04-25/

## External (MCP) writes (1)
- 5h ago — claude.ai wrote to memory:notes (subject: pricing strategy)

## System digests (1)
- 1d ago — back-office-narrative-digest rolled up 12 housekeeping invocations
```

Written via `services.authored_substrate.write_revision()` with `authored_by="system:narrative-digest"` per ADR-209 universal write path. Bounded ~1500 tokens. YARNNN reads on demand via `ReadFile` when the operator asks "what happened?" — most turns won't need it.

### `maybe_compact_history` is deleted

ADR-067 Phase 3's in-session LLM compaction (40K-token threshold; generates a `<summary>` block via Haiku call; persists to `chat_sessions.compaction_summary`) is **replaced wholesale** by the existing filesystem-native `conversation.md` (ADR-159 — written every 5 user messages). YARNNN reads `conversation.md` on demand via `ReadFile`.

Per singular-implementation discipline (rule 1):
- `api/routes/chat.py::maybe_compact_history()` — deleted.
- `COMPACTION_THRESHOLD`, `COMPACTION_PROMPT` constants — deleted.
- `truncate_history_by_tokens()` — deleted (the 10-message window is the singular truncation; token-based truncation was a backstop that the window already enforces).
- The `compaction_summary` column on `chat_sessions` becomes vestigial (no writers post-deletion). **Phase 2 follow-up** to drop the column — not blocking; not in this ADR's scope.

### Three principles

1. **Weight is the inclusion key, not recency.** Conversation rows pass through Layer 3 unconditionally. Non-conversation rows (system/reviewer/agent/external) re-enter via Layer 2 pointer at `recent.md`, where the `narrative_digest` task pre-filters by weight (material only, last 24h).

2. **Identity determines API representation, not inclusion.** Claude's API only accepts user/assistant. The ADR-219 enum widening is an internal storage decision; the API channel discipline is a separate concern. Layer 3 enforces the API channel; Layer 2 is the re-entry point for non-conversation Identities.

3. **Compaction is filesystem-write, not API-summary.** `conversation.md` (rolling 5-message-cadence) and `recent.md` (daily back-office) are the only compaction substrates. No in-session LLM summarization. Singular implementation.

### Citable Anthropic / Claude Code precedents

- **Skill-description + on-demand SKILL.md read**: Claude Code's canonical compact-pointer-plus-detail pattern. Skill descriptions cap at 1,536 chars combined; full SKILL.md loads on demand. This ADR's Layer 2 follows the exact pattern at the workspace level — ~30-token pointer + on-demand `ReadFile`.
- **"Tool outputs drop first, then conversation summarizes"**: Claude Code's documented auto-compaction policy. Commit B applies this at the message-window level (older tool turns collapse to summaries before the conversation budget is exhausted).
- **CLAUDE.md / auto-memory + on-demand reads**: Claude Code's hierarchy maps cleanly onto YARNNN's `/workspace/memory/{notes, awareness, conversation, recent}.md` set. Layer 2 makes that mapping legible in the prompt.

---

## Implementation (three commits, all landed 2026-04-26)

### Commit A (96b24d4) — bug fix: filter non-conversation roles from API history

`build_history_for_claude()` filters `role ∉ {user, assistant}` before constructing the API messages list. Test gate `api/test_adr220_history_filtering.py` — A1-A4 (4/4).

### Commit B (daec134) — older assistant tool-history collapsed to one-line summaries

Pre-compute `last_assistant_with_tools_idx` before the loop; only that turn keeps full structured `tool_use`/`tool_result` blocks. Older turns collapse to `[Called X: result]` text. Cites Claude Code's "tool outputs drop first" precedent. Two former branches consolidated into one keyed on `is_most_recent_with_tools` (singular implementation). Test gate B1-B3 (3/3).

### Commit C (this commit) — recent.md + compact-index pointer + maybe_compact_history sunset

- `api/services/back_office/narrative_digest.py::run()` extended: writes `/workspace/memory/recent.md` via `write_revision()` (`authored_by="system:narrative-digest"`) when there are material-weight non-conversation entries in the 24h window.
- `api/services/working_memory.py::format_compact_index()` adds a one-line pointer to `recent.md` when the file exists and has content. Stays under 600-token ceiling.
- `api/agents/yarnnn_prompts/tools_core.py` "Revision-Aware Reading" section gets a small note distinguishing the two complementary signals (substrate authorship via Revision primitives; narrative events via `ReadFile recent.md`).
- `api/routes/chat.py` deletes `maybe_compact_history()`, `COMPACTION_THRESHOLD`, `COMPACTION_PROMPT`, `truncate_history_by_tokens()`. The 10-message window is the singular truncation; `conversation.md` is the singular compaction substrate.
- `docs/features/sessions.md` refresh: "What carries over" table adds `recent.md`; "Contrast with Claude Code" closes the session_messages-only-user-assistant gap line; new "Layered context model" section maps L1/L2/L3.
- `CLAUDE.md` ADR list adds ADR-220.
- `docs/architecture/FOUNDATIONS.md` Axiom 9 section gains one sentence noting narrative rolls up to `recent.md` for prompt-time legibility.

Test gate (Commit C): assert recent.md is written when housekeeping/material entries exist; compact index includes the pointer when file exists; `maybe_compact_history` no longer importable; ADR-209 substrate-authorship signal still rendered (regression check); 600-token ceiling holds.

---

## Cost projection

Per chat turn under the new model (sustained alpha workload):

- Layer 1 static: ~13K tokens, ~95% cached → ~$0.0006 (~98% of the prompt that doesn't move)
- Layer 2 workspace state: ~700 tokens uncached → ~$0.002
- Layer 3 conversation window: ~2-3K tokens partially cached → ~$0.005
- **Total: ~$0.008 per turn input** vs ADR-159's targeted ~$0.018 → another ~55% on top of ADR-159's already-strong economics.

Cost reductions accrue from three places:
1. Removing the 40K-token in-session LLM compaction call (~$0.05 per long session, ~$0 now since `conversation.md` is filesystem-native).
2. Tool-history collapse on older turns (~30-60% input-token reduction on tool-heavy multi-turn sessions per Commit B).
3. Layer 2 pointers replace inline state dumps (the fundamental ADR-159 contribution, extended).

---

## What this preserves

- **ADR-159** filesystem-as-memory (extended; not replaced).
- **ADR-186** prompt profiles — Layer 1's behavioral profile selection is unchanged. Workspace vs entity profile resolution per `SURFACE_PROFILES` dict in `chat.py`.
- **ADR-209** Authored Substrate signal — Layer 2's first one-liner is the existing `_get_recent_authorship_sync()` line. Untouched.
- **ADR-219** narrative substrate — Layer 2's second one-liner reads from `session_messages`. The narrative-digest task gets one additional output.
- **ADR-067 Phase 1** (cross-session continuity via `awareness.md`) and **Phase 2** (4h inactivity boundary) — unchanged. Only Phase 3 in-session LLM compaction is sunset.

## What this supersedes

- **ADR-067 Phase 3** in-session LLM compaction. The 40K-token `maybe_compact_history` path is deleted. `conversation.md` is the singular compaction substrate.

---

## Test gate

Combined ADR-220 test totals (commits A + B + C):

- `api/test_adr220_history_filtering.py` — A1-A4 + B1-B3 = 7/7
- `api/test_adr220_layered_context.py` (Commit C) — 8/8 (recent.md written when entries exist; compact index pointer rendered; maybe_compact_history not importable; substrate authorship signal preserved; 600-token ceiling held)
- **Total: 15/15** across two ADR-220 test files.

All 40/40 ADR-219 test gates remain green: `test_adr219_narrative_write_path` (8) + `commit3_narrative_digest` (6) + `commit4_narrative_by_task` (10) + `commit5_chat_rendering` (12) + `invocation_coverage` (4).

Combined ADR-219 + ADR-220 test totals: **55/55**.

---

## Validation

After Commit C lands, three assertions hold:

1. **No invocation that produces a substrate mutation re-enters YARNNN's prompt twice.** Layer 2's two one-liners are orthogonal axes; the same event doesn't appear in both.

2. **YARNNN can answer "what happened while I was away?" without scrolling chat history.** It reads `recent.md` on demand. Operators get the curated answer without the model having to scan 10 messages of routine entries.

3. **Singular compaction substrate.** Search the codebase for in-session LLM compaction calls — only `conversation.md` write path remains. `maybe_compact_history` is gone.

---

## Open questions (deferred to follow-ups, not blocking)

1. **`chat_sessions.compaction_summary` column drop.** Vestigial after this ADR. Drop in a future schema-cleanup migration; not blocking. Existing rows can be ignored or hard-deleted at that time.

2. **Should `recent.md` be Identity-grouped or time-grouped?** Currently grouped by Identity class (reviewer / agent / external / system). Alternative: chronological with Identity tags. Chronological is more "log-like"; Identity-grouped is more "scannable for what kind of thing happened." Identity-grouped lands first; revisit after a week of operator use.

3. **Weight-keyed conversation window inclusion.** Currently the 10-message window is recency-only. Could bias toward "always include the last 3 material conversation entries even if they're outside the recency window." Rejected for now — it adds complexity and operator hasn't asked. Revisit if "YARNNN forgot what we decided yesterday" becomes a complaint.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-04-26 | v1 — Initial proposal + Commits A + B + C all landed in single ADR. Three-layer context model with two complementary one-liners in Layer 2. Filesystem-native rollup via `recent.md`. Sunset of `maybe_compact_history`. 15/15 test gate. |
