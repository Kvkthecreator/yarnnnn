# Surface-Action Mapping — Design Principle

**Date:** 2026-03-10
**Status:** Active
**Related:**
- [Surface Architecture](SURFACE-ARCHITECTURE.md) v3 — Chat + Agents + Context + Activity
- [Inline Plus Menu](INLINE-PLUS-MENU.md) — action verb taxonomy
- [ADR-105: Instructions to Chat Surface](../adr/ADR-105-instructions-chat-surface-migration.md) — implementation plan
- [Workspace Layout & Navigation](archive/WORKSPACE-LAYOUT-NAVIGATION.md) — archived layout structure

---

## Principle

Every piece of UI in YARNNN lives on one of two surfaces. The surface determines what kind of interaction it supports:

| Surface | Purpose | Interaction model |
|---------|---------|-------------------|
| **Chat/Inline** | Actions, directives, feedback | Conversational — user tells TP, TP responds |
| **Drawer** | Reference, configuration, navigation | Direct manipulation — user edits fields, browses lists |

**The rule:** Things that change agent behavior flow through **chat**. Things that configure structural settings or display accumulated state live in the **drawer**.

---

## Why two surfaces

YARNNN has one agent (TP) operating in two modes: conversational (chat) and autonomous (headless execution). The user needs to:

1. **Direct the agent** — "focus on action items", "this report is for my CTO", "ignore the #random channel noise"
2. **Configure the system** — when to run, which sources to read, where to deliver

These are fundamentally different interactions. Directives are contextual and benefit from TP acknowledging them ("Got it — I'll emphasize action items going forward"). Configuration is structural and benefits from direct manipulation (dropdown for schedule, checkbox for sources).

Mixing them creates confusion: a form field for instructions looks like configuration but acts like a directive. A chat message about schedule feels conversational but is really just setting a cron.

---

## The distinction: Directives vs Configuration

**Directives** — what the agent should care about, how it should behave:
- Behavioral instructions ("use formal tone", "always include TL;DR")
- Audience/recipient context ("this is for my manager who cares about metrics")
- Feedback on output ("too verbose", "missing the Notion updates")
- Priority signals ("focus on the #engineering channel this week")

→ These belong in **chat/inline**. TP processes them, acknowledges, and persists to `agent_instructions` or `agent_memory`.

**Configuration** — structural settings that define the agent's operating parameters:
- Schedule (frequency, day, time, timezone)
- Data sources (which channels, labels, pages to read)
- Destination (where to deliver: email, Slack, Notion)
- Title (naming)
- Status (active/paused/archived)

→ These belong in the **drawer**. Direct manipulation via form fields. No TP involvement needed.

**Reference** — accumulated state the user views but doesn't directly edit:
- Version history (browsing past outputs)
- Memory/observations (what the agent has learned)
- Session history (past conversations)
- Source snapshots (what data was used)

→ These belong in the **drawer**. Read-only or navigation-only surfaces.

---

## Surface mapping

### Chat/Inline surface

| What | Verb | How |
|------|------|-----|
| Set/update instructions | prompt | User says it → TP persists to `agent_instructions` |
| Define audience | prompt | User describes recipient → TP persists to `recipient_context` |
| Give version feedback | panel | Feedback strip on version preview in panel |
| Request generation | execute | + menu "Generate new version" |
| Ask about agent | chat | Scoped conversation (TP has agent context) |
| Create new agent | show | Type selector cards from + menu |

### Drawer surface

| What | Tab | Interaction |
|------|-----|-------------|
| Schedule | Settings | Dropdowns (frequency, day, time) |
| Data sources | Settings | SourcePicker (visual grid) |
| Destination | Settings | Form fields |
| Title | Settings | Text input |
| Archive | Settings | Button with confirmation |
| Version list | Versions | Click to select, view inline |
| Memory/observations | Memory | Read-only timeline |
| Sessions | Sessions | Navigation list |

### Panel (persistent right panel)

| What | Purpose |
|------|---------|
| Version preview | Full markdown render of selected version |
| Version list | Compact list, click to preview |
| Source pills | What sources contributed (in version preview) |
| Feedback strip | Leave feedback on delivered versions |

---

## The + menu verb taxonomy

Each action in the + menu has an explicit verb type (from [INLINE-PLUS-MENU.md](INLINE-PLUS-MENU.md)):

| Verb | Behavior | Example |
|------|----------|---------|
| **show** | Renders inline UI component | Type selection cards |
| **execute** | Fires immediately | Generate new version |
| **prompt** | Pre-fills input for user to refine | "Update instructions for..." |
| **attach** | Opens system dialog | File picker |

The verb determines the interaction pattern. Never default to "pre-fill text" — each action must be explicitly mapped.

---

## What this means for the Instructions tab

The current Instructions drawer tab (behavior textarea + audience fields + prompt preview) violates this principle. It's an **action surface** (changing agent behavior) styled as a **dashboard panel** (form fields in a drawer).

[ADR-105](../adr/ADR-105-instructions-chat-surface-migration.md) addresses this by migrating instruction editing to the chat surface while keeping a read-only view in the drawer.

---

## Edge cases and nuance

**Not everything is cleanly one or the other:**

1. **Quick edits to existing instructions** — If the user just wants to add one line to instructions, opening a chat feels heavy. The drawer could keep a read-only view with an "Edit in chat" affordance, or allow lightweight inline edits that TP acknowledges asynchronously.

2. **Bulk source changes** — "Add all my Slack channels" is conversational, but the visual SourcePicker grid is better for selecting specific channels. Configuration UIs can still be the best tool — the principle is about where the interaction *starts*, not that everything must be a chat message.

3. **First-time setup** — During agent creation, the user needs to set everything at once (type, sources, schedule, instructions). This is a wizard flow that mixes configuration and directives. The creation flow is its own surface that doesn't need to follow the steady-state mapping.

---

## Surface mapping (updated for v3 architecture)

Four surfaces, each with clear interaction boundaries:

| Surface | Route | Primary Interaction |
|---------|-------|---------------------|
| **Chat page** | `/chat` | Directives + strategic conversation — unscoped TP |
| **Agents page** | `/agents` | Agent management + task steering — agent/task-scoped TP |
| **Context page** | `/context` | Reference + browsing — workspace-scoped TP |
| **Activity page** | `/activity` | Observation only — no chat, no actions |

The chat page is the primary **directive** surface (tell TP what to do).
The agents page mixes **directive** (steer via chat panel) and **reference** (view domain/outputs).
The context page is primarily **reference** (browse workspace files) with light directive ability.

See [SURFACE-PRIMITIVES-MAP.md](SURFACE-PRIMITIVES-MAP.md) for the full primitive/action mapping per surface.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-10 | Initial principle — surface-action mapping with directive vs configuration distinction |
| 2026-04-04 | Updated surface mapping for v3 architecture (Chat + Agents + Context + Activity) |
