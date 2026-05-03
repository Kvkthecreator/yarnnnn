> **SUPERSEDED 2026-05-03** — Canonical reference is now [docs/architecture/workspace-init.md](../../../architecture/workspace-init.md). CONVENTIONS.md is no longer kernel-seeded; it is program-scoped. Archived for historical context.

# Shared Context Workflow — ADR-144

**Extended by:** ADR-155 — identity writes now trigger workspace-wide inference cascade (domain scaffolding across all context domains).
**Extended by:** ADR-226 — when a program bundle is selected at signup, IDENTITY/BRAND/MANDATE/CONVENTIONS arrive as `authored`-tier files with `prompt:` frontmatter; the activation overlay walks YARNNN through them in declared order. UpdateContext remains the singular write path.

How users create and update workspace shared context (IDENTITY.md, BRAND.md, CONVENTIONS.md, MANDATE.md).

## Principle

**Inference is the method, not the product.** Users express intent ("update my identity"), the system infers from whatever sources are available (documents, URLs, chat text, platform content). No form fields. Workspace files ARE the context — no separate structured storage.

## Bundle-Seeded Skeletons (post-OS-pivot 2026-04-27)

When `initialize_workspace(program_slug=...)` runs, the program bundle's `reference-workspace/` is forked into the operator's `/workspace/`. Per ADR-223 §5 + ADR-226, `_shared/` files arrive in three tiers:

| Tier | Behaviour at fork | Behaviour on re-fork | Examples (alpha-trader) |
|---|---|---|---|
| `canon` | Copied verbatim, frontmatter stripped | Re-applied if differs (operator edits preserved as prior revisions per ADR-209) | CONVENTIONS.md, AUTONOMY notes |
| `authored` | Copied as skeleton + `prompt:` frontmatter (stripped on write) | Preserved if operator filled, re-applied only if still skeleton | IDENTITY.md, MANDATE.md, principles.md |
| `placeholder` | Copied empty | Never overwritten | per-instrument folders, _performance.md |

**Implication for this workflow:** `authored`-tier shared files arrive *prompt-bearing*. The activation overlay (`api/agents/yarnnn_prompts/activation.py`) surfaces each prompt as YARNNN's question; operator responses route through the existing `UpdateContext` primitive. The write path is unchanged — singular implementation preserved. The only thing the bundle adds is a **declared walking order** for the activation conversation.

**When no program is selected:** workspace receives kernel-default empty skeletons (the pre-pivot path). The cold-start ContextSetup flow below applies.

## Current Surface Model (ADR-163 + ADR-180 — v12 four-surface nav)

`/context` (Files) owns the workspace filesystem: domains, outputs, uploads, settings.
`/chat` (home) owns ContextSetup for cold-start via Onboarding modal (ADR-165 v8).
Identity/Brand files are browsable at `/context` under Settings; inference provenance rendered by `InferenceContentView`.

```
/context  (Files)
  ├─ Context/   — accumulated domain knowledge
  ├─ Outputs/   — task deliverable outputs
  ├─ Uploads/   — user-contributed files
  └─ Settings/
       ├─ IDENTITY.md
       ├─ BRAND.md
       └─ AWARENESS.md
```

TP decides which target (identity vs brand) based on conversation context via `UpdateContext(target=...)` primitive (ADR-146). No user-facing distinction needed. Plus-menu label is "Update workspace" (v12).

### Cold Start (Empty Workspace)

New users land on `/chat`. TP's first turn detects empty workspace state and emits `<!-- workspace-state: {"lead":"context"} -->`, opening the Onboarding modal with `ContextSetup`. See [ONBOARDING-TP-AWARENESS.md](ONBOARDING-TP-AWARENESS.md) for the full flow.

Chat suggestion chips (static, shown when history is empty):
- "Tell me about my work and who I serve"
- "Set up competitive intelligence tracking"
- "Create a weekly Slack recap"

Chips disappear once the user sends any message.

### Populated State

- **Identity/Brand**: `InferenceContentView` renders IDENTITY.md/BRAND.md with source provenance caption + gap banner (ADR-162/163)
- **Uploads**: File list accessible under `/context` Uploads section

## Update Flows

### Flow 1: Via Chat (Primary)

```
User: "Update my identity — I'm Sarah, VP Eng at Acme Corp, we build developer tools"
  → TP calls UpdateSharedContext(target="identity", text="...")
  → Inference generates IDENTITY.md content
  → Writes to /workspace/IDENTITY.md
  → TP responds with summary of what was written

User: "Update my brand from acme.com"
  → TP calls WebSearch/WebFetch for acme.com
  → TP calls UpdateSharedContext(target="brand", url_contents=[...])
  → Inference generates BRAND.md content
  → Writes to /workspace/BRAND.md

User: "Update my identity from the pitch deck I uploaded"
  → TP reads document content
  → TP calls UpdateSharedContext(target="identity", document_ids=[...])
  → Inference merges with existing IDENTITY.md
```

### Flow 2: Direct Edit (Fallback)

User clicks "Edit" on Identity/Brand tab → raw markdown textarea → Save.
No inference involved. Direct write to workspace file.

### Flow 3: Future — Continuous Enrichment

When new documents are uploaded or platforms sync fresh content, TP can suggest:
"I see you uploaded new brand guidelines. Want me to update your brand context?"

## Inference Sources (Priority Order)

1. **Chat text** — user's direct description (highest signal)
2. **Uploaded documents** — pitch decks, brand guidelines, strategy docs
3. **URLs** — company website, LinkedIn, blog (via WebSearch/WebFetch)
4. **Platform content** — Slack channels, Notion pages (via Search)
5. **Existing file** — current IDENTITY.md/BRAND.md (for merge, not overwrite)

## Context Readiness Signal

Working memory includes a `workspace_state` object so TP knows what's sparse:

```json
{
  "identity": "empty",      // empty | sparse | rich
  "brand": "empty",
  "documents": 0,
  "tasks": 0
}
```

TP uses this with judgment — there is no hard gate between context enrichment and task
creation. A sparse identity with a clear role is enough for TP to suggest tasks.
Priority order: Identity → Brand → Tasks, but the user is never blocked.

## Onboarding Dissolution

The `/onboarding` page is replaced by this workflow (ADR-132, ADR-144). New users land on `/chat` with:
- Pre-scaffolded agent roster (ADR-176)
- TP that detects empty workspace state and opens the Onboarding modal
- No separate onboarding step — `/chat` is the onboarding surface

See [ONBOARDING-TP-AWARENESS.md](ONBOARDING-TP-AWARENESS.md) for the full flow and modal design.

### TP Context Awareness

The context awareness prompt is **always injected** into TP's system prompt (not gated
by any onboarding flag). TP sees `workspace_state` signals in working memory every
turn and uses judgment to guide the user. Platform connections are not a prerequisite —
they enrich context but don't gate it.
