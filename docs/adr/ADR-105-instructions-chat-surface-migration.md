# ADR-105: Instructions to Chat Surface Migration

**Date:** 2026-03-10
**Status:** Implemented (Phase 1)
**Supersedes:** None
**Related:**
- [ADR-104: Agent Instructions Unified Targeting](ADR-104-agent-instructions-unified-targeting.md) — instructions as the single targeting layer
- [ADR-087: Agent Scoped Context](ADR-087-agent-scoped-context.md) — per-agent instructions + memory
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — one agent, two modes
- [Surface-Action Mapping](../design/SURFACE-ACTION-MAPPING.md) — design principle

---

## Context

ADR-104 established `agent_instructions` as the unified targeting layer — user intent for "what this agent should focus on" flows through a single text field, dual-injected into the headless system prompt (behavioral constraints) and the type prompt user message (priority lens).

The current UI surface for editing instructions is the **Instructions drawer tab**: a textarea for behavior directives, collapsible audience fields (name, role, notes), and a prompt preview. This works but creates a design inconsistency:

1. **Instructions are directives, not configuration.** They change how the agent behaves — closer to "telling TP what to do" than "configuring a setting." The [Surface-Action Mapping](../design/SURFACE-ACTION-MAPPING.md) principle says directives should flow through chat.

2. **TP can't acknowledge or refine.** When the user types instructions in a drawer textarea, there's no feedback loop. TP doesn't see the edit until the next execution run. In chat, TP can acknowledge ("Got it — I'll focus on action items"), suggest refinements ("Do you want me to also track blockers?"), and persist immediately.

3. **Recipient context is conversational by nature.** "This report is for my CTO Sarah who cares about velocity metrics" is a natural chat utterance that TP can parse into structured fields. A form with name/role/notes fields is the less natural interface.

4. **The dashboard chat already shows TP can't explain generation context** (screenshot 2 from the discussion). When a user asks "what context was used for v3?", TP can't answer because it lacks provenance. Moving instructions to chat creates a natural place for the user to ask "what are my current instructions?" and get an answer.

---

## Decision

Migrate instruction editing from the drawer to the chat surface. The drawer Instructions tab becomes a **read-only reference view** showing current instructions and audience context.

### Phase 1: Chat-mediated instruction editing

**What changes:**

1. **+ menu action**: Add "Update instructions" as a `prompt` verb action in the agent chat + menu (already exists — pre-fills "I want to update the instructions for this agent").

2. **TP instruction write primitive**: New `Edit` primitive action for `agent_instructions` and `recipient_context`. When the user says "focus on action items" or "this is for my CTO Sarah", TP:
   - Parses the intent
   - Calls `Edit(ref="agent:<id>", field="instructions", value="...")` or `Edit(ref="agent:<id>", field="recipient_context", value={...})`
   - Acknowledges: "Updated — I'll focus on action items in future versions."

3. **Instructions tab → read-only**: The drawer Instructions tab shows:
   - Current `agent_instructions` text (read-only, monospace)
   - Current `recipient_context` summary (read-only)
   - Prompt preview (unchanged — shows what the agent sees)
   - "Edit in chat" affordance (button that focuses chat input with pre-filled prompt)

4. **Working memory injection**: TP already gets instructions via `_extract_agent_scope()` in working memory. No change needed — TP can answer "what are my current instructions?" from existing context.

**What doesn't change:**
- `agent_instructions` field and dual-injection (ADR-104)
- Headless system prompt composition
- Settings tab (schedule, sources, destination, title) — these are configuration, not directives
- Memory tab — remains read-only
- Sessions tab — remains navigation

### Phase 2: Audience context via chat (deferred)

Recipient context (name, role, priorities, notes) could also be set conversationally: "this agent is for the engineering leadership team, they care about velocity and blockers." TP would parse this into the structured `recipient_context` JSONB.

This is deferred because:
- The current audience fields work adequately for the small number of users who set them
- Parsing natural language to structured recipient fields requires prompt engineering
- Instructions are the higher-impact migration (used by every agent, audience is optional)

### Phase 3: Prompt preview enhancement (deferred)

The prompt preview currently uses a client-side `composePromptPreview()` that approximates what the agent sees. This could be replaced with an actual backend endpoint that returns the composed prompt, making the preview authoritative rather than approximate.

---

## Implementation

### Backend (already supported)

The Edit primitive in `api/services/primitives/edit.py` already handles `agent_instructions` and `recipient_context` as direct field updates on the agent entity. The primitive is mode-gated to `["chat"]` only — headless agents cannot self-modify instructions.

**File: `api/agents/tp_prompts/behaviors.py`** (updated)

Added "Update audience" guidance to the Agent Workspace Management section, with an explicit `Edit` example for persisting `recipient_context` when users describe who a agent is for. The existing guidance already covered instructions and observations.

**File: `api/agents/tp_prompts/tools.py`** (updated)

Added "Audience" field documentation to the Agent Workspace section, with an `Edit` primitive example for `recipient_context`.

### Frontend (implemented)

**File: `web/components/agents/AgentDrawerPanels.tsx`**

Converted `InstructionsPanel` from an editable form to a read-only reference view:
- Replaced textarea with read-only monospace display of current instructions
- Replaced audience form fields with read-only summary
- Kept prompt preview (collapsible)
- Added "Edit in chat" button that pre-fills the chat input with an instruction update prompt

**File: `web/app/(authenticated)/agents/[id]/page.tsx`**

- Removed `instructions`, `recipientContext` state management (no longer edited inline)
- Removed `saveInstructionFields`, `scheduleSave`, debounce logic, refs
- Instructions state read from agent data (refreshed from API)
- Added `prefillChatRef` to wire "Edit in chat" button to the chat input

**File: `web/components/agents/AgentChatArea.tsx`**

- Added `prefillChatRef` prop to allow external callers (drawer "Edit in chat" button) to pre-fill and focus the chat input
- No structural changes — the + menu already has "Update instructions" as a prompt verb

---

## Files modified

| File | Change |
|------|--------|
| `api/services/primitives/edit.py` | Already supported — no changes needed |
| `api/agents/tp_prompts/behaviors.py` | Added recipient_context editing guidance |
| `api/agents/tp_prompts/tools.py` | Added Audience field documentation |
| `web/components/agents/AgentDrawerPanels.tsx` | InstructionsPanel → read-only reference view |
| `web/app/(authenticated)/agents/[id]/page.tsx` | Removed instruction editing state, simplified to read-only |
| `web/components/agents/AgentChatArea.tsx` | Added prefillChatRef for "Edit in chat" wiring |
| `docs/design/SURFACE-ACTION-MAPPING.md` | Design principle (written) |
| `api/prompts/CHANGELOG.md` | Log prompt changes |

---

## What this does NOT change

- `agent_instructions` as the unified targeting field (ADR-104)
- Dual injection into system prompt + user message
- Settings tab (schedule, sources, destination) — configuration stays in drawer
- Memory tab — remains read-only reference
- Headless execution pipeline — unchanged
- Dashboard chat — no agent editing there (no agent context)

---

## Risks

1. **Friction increase for quick edits** — Typing "change tone to formal" in chat is more keystrokes than editing a textarea. Mitigated by the "Edit in chat" affordance and the + menu prompt verb.

2. **TP parsing reliability** — TP must correctly parse "focus on blockers" into an instruction update, not just respond conversationally. Mitigated by explicit system prompt guidance and the Edit primitive providing a clear action path.

3. **State sync** — After TP edits instructions via the Edit primitive, the drawer's read-only view must refresh. Requires either a re-fetch trigger or optimistic UI update from the chat stream.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-10 | Initial proposal |
| 2026-03-10 | Phase 1 implemented — backend Edit primitive already supported; prompt guidance added; frontend InstructionsPanel converted to read-only; instruction editing state removed from page.tsx |
