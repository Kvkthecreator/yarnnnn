# Onboarding & TP Awareness — Design Brief

**Status:** Active (v2 — consolidated on /chat page)
**Date:** 2026-04-04
**Supersedes:** v1 (2026-04-01, onboarding on /context setup-phase hero)
**Depends on:** [SURFACE-ARCHITECTURE.md](SURFACE-ARCHITECTURE.md) v3, ADR-155 (workspace inference)

---

## The Model: Chat Is Onboarding

Onboarding lives entirely on `/chat`. New users (0 tasks) are redirected here from auth callback. The ContextSetup component renders as the chat empty state — URLs, files, and free-text notes that bootstrap workspace identity. After the first interaction, it's a normal chat.

```
Sign up → auth callback → check tasks → 0 tasks → /chat (onboarding)
                                       → 1+ tasks → /agents (returning user)
```

### Why /chat

1. **TP is the single intelligence layer.** Onboarding inputs (URL, file, text) are messages to TP. TP calls `UpdateContext` + `ManageDomains` to scaffold the workspace. No separate onboarding service.
2. **Full-width gives space.** ContextSetup has URL inputs, file upload, textarea. A 380px chat sidebar is too cramped. Full-page `/chat` gives it room.
3. **Clean separation.** The agents page is for supervising work. The context page is for browsing files. Neither should double as an onboarding wizard.

---

## Cold-Start Flow

### Empty State: ContextSetup

When `/chat` has no messages, `ContextSetup` renders as the empty state:

| Section | Input | What happens |
|---|---|---|
| **Links** | Paste URLs (company website, LinkedIn) | Composed into message, TP infers identity |
| **Files** | Upload PDF, DOCX, TXT, MD | Uploaded to workspace, text extracted, TP infers identity |
| **Notes** | Free-text textarea | Composed into message, TP processes |
| **Skip options** | "What can you track for me?" / "I want to create a task" | Sends message directly to TP |

On submit, all inputs compose into a single TP message. ContextSetup disappears. TP responds and the page is a normal chat from here.

### TP Processing

TP receives the composed message and calls:
1. `UpdateContext(target="identity")` — scaffolds IDENTITY.md from inferred content
2. `ManageDomains({entities: [...]})` — scaffolds context domain folders from inferred entities
3. Responds with summary + next suggestion (e.g., "I've set up your workspace. Want me to create a competitive tracking task?")

### Post-Onboarding Navigation

After TP scaffolds the workspace, NAVIGATE ui_actions from `CreateTask` direct to `/agents`. The user naturally transitions from `/chat` (directing) to `/agents` (supervising).

---

## TP Prompt Guidance

The `onboarding.py` prompt provides context-aware nudging:

- **context_readiness** in working memory: identity/brand/docs/tasks richness (empty|sparse|rich)
- **Priority order**: identity → brand → tasks (one thing at a time)
- **Philosophy**: suggest the ONE next step, don't enumerate all gaps

TP judges based on workspace state. If identity is empty, it asks about the user's work. If identity is rich but no tasks, it suggests task creation. This is prompt-level guidance, not mechanical rules.

---

## What Changed (v1 → v2)

| v1 (context page onboarding) | v2 (/chat onboarding) |
|---|---|
| `/context` detected setup phase, rendered ContextSetup as hero | `/chat` renders ContextSetup as empty state |
| Auth callback always landed on `/agents` (HOME_ROUTE) | Auth callback checks tasks → new users → `/chat` |
| Agents page showed ContextSetup in chat panel | Agents page shows simple chat empty state |
| Two onboarding paths (context hero + agents chat panel) | One onboarding path (/chat) |
| Context page had dual role (onboarding + browsing) | Context page is pure browsing |

---

## ContextSetup Usage (Canonical)

`ContextSetup` is used in exactly one place:

| Surface | Usage | Purpose |
|---|---|---|
| `/chat` | Empty state (no messages) | Onboarding + context updates |

Previously also used in `/context` (setup hero) and `/agents` (chat empty state) — both removed.

---

## References

- `web/app/(authenticated)/chat/page.tsx` — chat page with ContextSetup as empty state
- `web/components/tp/ContextSetup.tsx` — the onboarding input component
- `api/agents/tp_prompts/onboarding.py` — TP onboarding prompt guidance
- `api/services/working_memory.py` — context_readiness signals
- `web/app/auth/callback/page.tsx` — new user detection + /chat redirect
