# Shared Context Workflow — ADR-144

How users create and update workspace shared context (IDENTITY.md, BRAND.md).

## Principle

**Inference is the method, not the product.** Users express intent ("update my identity"), the system infers from whatever sources are available (documents, URLs, chat text, platform content). No form fields. Workspace files ARE the context — no separate structured storage.

## Workfloor Surface (v4 — overlay layout, 2026-03-30)

Floating panels over isometric room backdrop. Left panel has tabbed Tasks/Context:

```
Tasks           — active task list, links to task pages
Context         — nested sub-navigation:
  ├─ Identity   — rendered IDENTITY.md
  ├─ Brand      — rendered BRAND.md
  └─ Documents  — uploaded file list
```

### Button Consolidation (2026-03-30)

"Update my identity" and "Update my brand" consolidated into single **"Update context"** across all surfaces:
- **Bottom action bar**: "Update Context" button → sends "Update my context" to TP
- **PlusMenu**: Single "Update context" entry (was separate identity/brand)
- **Suggestion chips**: "Update my context" (was "Adjust focus for a task")
- **Context sub-tabs**: Each tab retains "Update via chat →" for targeted updates

TP decides which target (identity vs brand) based on conversation context via `UpdateContext(target=...)` primitive (ADR-146). No user-facing distinction needed.

### Cold Start (Empty Workspace)

**Chat suggestion chips**: When chat history is empty, the chat panel shows clickable
suggestion chips that send a message to TP on click:
- "Tell me about myself and my work" → triggers identity enrichment flow
- "Help me get set up" → TP uses judgment on readiness
- "What deliverables can you create for me?" → triggers task creation flow

Chips disappear once the user sends any message (conversation replaces them).
No LLM call on page load — chips are static frontend, TP only fires on interaction.

Each context sub-tab also shows guidance when empty:

- **Identity**: "Your identity helps agents understand who you are. Try: 'Update my context — I'm [name], [role] at [company]'"
- **Brand**: "Your brand guide shapes how agents write. Try: 'Update my brand from our website'"
- **Documents**: "Upload files via chat input (+) or drag & drop"

"Or edit manually" link available as fallback — opens raw markdown editor.

### Populated State

- **Identity/Brand**: Rendered markdown + "Edit" link for manual adjustment
- **Documents**: File list with processing status + size

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

Working memory includes a `context_readiness` object so TP knows what's sparse:

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

The `/onboarding` page is replaced by this workflow. New users land on `/workfloor` with:
- Pre-scaffolded agent roster (ADR-140)
- Empty Context tabs with guidance
- TP chat that detects empty context and guides enrichment

No separate onboarding step. The workfloor IS the onboarding surface.

### TP Context Awareness

The context awareness prompt is **always injected** into TP's system prompt (not gated
by any onboarding flag). TP sees `context_readiness` signals in working memory every
turn and uses judgment to guide the user. Platform connections are not a prerequisite —
they enrich context but don't gate it.
