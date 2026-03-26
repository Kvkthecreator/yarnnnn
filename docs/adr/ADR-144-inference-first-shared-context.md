# ADR-144: Inference-First Shared Context

**Status:** Implemented (Phases 1-4)
**Date:** 2026-03-26
**Supersedes:** ADR-132 (onboarding page), ADR-113 (onboarding flow)
**Extends:** ADR-106 (workspace), ADR-138 (agents as work units), ADR-140 (workforce model), ADR-142 (unified filesystem)

## Context

Workspace shared context (IDENTITY.md, BRAND.md) is the upstream input for all task scaffolding and agent execution. Currently:

1. **Onboarding page** (`/onboarding`) — separate page with form fields (name, work description, file upload). Runs `enrich_context()` once, writes workspace files, never revisited.
2. **Profile API** (`/api/memory/profile`) — structured fields (name/role/company/timezone) stored separately from IDENTITY.md. Two sources of truth.
3. **Identity tab on workfloor** — renders profile fields as form inputs, not the actual IDENTITY.md content.
4. **Brand tab** — renders BRAND.md but editing is raw markdown textarea.

Problems:
- **Form fields are fake precision.** "Role: CEO" is thin. Inference from a pitch deck produces richer context.
- **Onboarding is a dead end.** Filled once, never enriched again. But context is continuous — new docs, new platforms, new conversations.
- **Two sources of truth.** Profile API fields vs. IDENTITY.md content diverge.
- **TP has no enrichment primitive.** Can't update shared context from conversation.
- **No context richness signal.** TP doesn't know if workspace context is sparse or rich — can't guide users toward enrichment.

## Decision

**Inference is the single method for shared context creation and update.** No form fields. No separate onboarding page. One primitive: `UpdateSharedContext`.

### Core Principle

The user intent is simple: **"update my identity"** or **"update my brand."** The *how* (inference from documents, URLs, chat text, platform content) is an implementation detail. The workspace file IS the context — no separate structured fields.

### Single Primitive

```
UpdateSharedContext(
    target: "identity" | "brand",
    # TP gathers sources before calling — these are what inference reads:
    text: str,                         # from user's chat message
    document_ids: list[str],           # from uploaded documents
    url_contents: list[dict],          # from WebSearch/WebFetch results
    platform_content: list[dict],      # from platform search results
)
```

TP orchestrates source gathering. User says:
- "Update my identity" → TP asks what to work from, or reads existing docs/platforms
- "Update my brand from my website" → TP fetches URL → feeds to inference → writes BRAND.md
- "Here's my pitch deck, update everything" → TP reads doc → runs inference for both targets

The primitive calls `infer_shared_context()` which:
1. Reads all provided sources
2. Reads existing workspace file (for merge, not overwrite)
3. Generates rich markdown via Sonnet
4. Writes to `/workspace/IDENTITY.md` or `/workspace/BRAND.md`
5. Returns what changed (for TP to summarize to user)

### Inference Sources

| Source | How TP gathers it | Feed to inference |
|--------|-------------------|-------------------|
| Uploaded documents | Already in workspace, referenced by ID | Document content (text extracted) |
| URLs | TP calls `WebSearch` / `WebFetch` | Page content / search results |
| Chat text | User's message in conversation | Raw text |
| Platform content | TP calls `Search` / `FetchPlatformContent` | Slack messages, Notion pages |
| Existing workspace file | Read current IDENTITY.md / BRAND.md | For merge context |

### Inference Function

```python
async def infer_shared_context(
    target: Literal["identity", "brand"],
    text: str = "",
    document_contents: list[dict] = [],   # [{filename, content}]
    url_contents: list[dict] = [],        # [{url, content}]
    platform_content: list[dict] = [],    # [{source, content}]
    existing_content: str = "",           # current file content for merge
) -> str:
    """Returns markdown content for the target workspace file."""
```

**Identity inference** produces:
```markdown
# Identity

## Who
[Name], [Role] at [Company]
[Industry/space]. [2-3 sentence context summary.]

## Domains of Attention
- [Domain 1]: [why this matters]
- [Domain 2]: [why this matters]

## Work Patterns
- [Pattern 1]: [cadence, what it involves]
- [Pattern 2]: [cadence, what it involves]

## Timezone
[Inferred or stated]
```

**Brand inference** produces:
```markdown
# Brand

## Voice
[1-2 sentences describing communication style]

## Tone
[Professional/casual/technical/etc. with nuance]

## Terminology
- [Term]: [how they use it]
- [Term]: [how they use it]

## Audience
[Who they typically communicate with]

## Style Notes
- [Specific observation from their materials]
```

### Workfloor Surface — Nested Context Tab

Replace flat 5-tab layout with nested structure:

```
Tasks
Context
  ├─ Identity    (rendered IDENTITY.md + "Update" button)
  ├─ Brand       (rendered BRAND.md + "Update" button)
  └─ Documents   (file list + upload)
```

Two top-level sections (Platforms tab removed — platforms are infrastructure, not context). Context expands to show workspace files as sub-navigation. Scales to additional files (PLAYBOOK.md, CONTEXT.md) without adding top-level tabs.

**"Update" button** sends a message to TP chat: "Update my identity" / "Update my brand". TP then orchestrates the inference flow — asks what sources to use, gathers them, runs inference, writes the file.

**Identity tab** renders IDENTITY.md as markdown (read-only display + "Update" button). No form fields. Direct markdown edit available as fallback ("Edit" link → raw markdown textarea).

**Brand tab** renders BRAND.md as markdown. Same pattern.

### Cold Start (Replaces Onboarding Page)

When workspace context is empty (IDENTITY.md doesn't exist or is skeleton), workfloor shows cold start state:

```
Context
  ├─ Identity    "Tell me about yourself — upload a doc, share a URL, or just describe your work"
  ├─ Brand       "Share your brand guidelines, website, or pitch deck"
  └─ Documents   "Upload files your agents should know about"
```

TP working memory includes a **context readiness** signal:

```python
"context_readiness": {
    "identity": "empty" | "sparse" | "rich",
    "brand": "empty" | "sparse" | "rich",
    "documents": 0,
    "platforms_connected": 1,
    "tasks": 0,
}
```

TP prompt awareness: "User has sparse workspace context. Before creating tasks, guide them toward enriching identity and brand. Suggest: 'Want to update your identity? Upload a doc or tell me about your work.'"

### What Gets Deleted

- `/onboarding` page (web/app/onboarding/) — cold start handled by workfloor
- `/api/memory/profile` endpoint (structured fields) — IDENTITY.md is the profile
- `enrich_context()` as standalone function — logic moves into `UpdateSharedContext` primitive
- `is_onboarding` binary flag — replaced by `context_readiness` assessment
- `ONBOARDING_CONTEXT` prompt — replaced by graduated TP awareness of context richness
- Profile form fields in Identity tab — replaced by rendered IDENTITY.md

### What's Preserved

- Document upload (moves to Documents sub-tab under Context)
- Workspace files (IDENTITY.md, BRAND.md remain the source of truth)
- Agent roster scaffolding at sign-up (ADR-140 unchanged)
- Platform connection flow (unchanged)

## Phases

### Phase 1: Primitive + Inference ✅
- `UpdateSharedContext` primitive in `api/services/primitives/shared_context.py` (chat-only)
- `infer_shared_context()` in `api/services/context_inference.py` (replaces `enrich_context()`)
- Context readiness signal in `build_working_memory()` — `{identity, brand, documents, tasks}` richness
- Graduated `CONTEXT_AWARENESS_PROMPT` (replaces binary `ONBOARDING_CONTEXT`)

### Phase 2: Workfloor Surface ✅
- Nested Context tab (Identity / Brand / Documents sub-nav)
- Identity tab renders IDENTITY.md markdown (not form fields) + "Update via chat" button
- Brand tab renders BRAND.md markdown + "Update via chat" button
- Cold start empty states with inference guidance
- New API: `GET/POST /api/memory/user/identity` (mirrors brand pattern)

### Phase 3: Onboarding Dissolution ✅
- Deleted `/onboarding` page
- Deleted `POST /user/onboarding` endpoint
- Deleted `onboarding.enrich()` client method
- Auth callback triggers roster scaffolding, redirects to `/workfloor`
- Profile form fields dissolved — IDENTITY.md is the profile
- Removed `/onboarding` from middleware protected prefixes

### Phase 4: Continuous Enrichment ✅
- TP prompt extended with proactive suggestion guidance for doc uploads, URL searches, platform connections
- One-time-per-session suggestion discipline to avoid nagging
- TP offers to update identity/brand when relevant source material appears in conversation

## Consequences

**Positive:**
- Single source of truth for shared context (workspace files)
- Continuous enrichment vs. one-shot onboarding
- Richer context from inference vs. thin form fields
- TP can orchestrate context building conversationally
- Scales to additional workspace files without new primitives

**Negative:**
- Inference has LLM cost per update (~$0.01-0.03 per call)
- Users can't quick-edit name/timezone without going through inference (mitigated by raw markdown edit fallback)
- Cold start requires TP engagement (no self-service form)

**Risks:**
- Inference quality varies — bad pitch deck → bad IDENTITY.md. Mitigated by: merge with existing content, user can re-run or manually edit.
- "Update my identity" is vague — TP needs good heuristics for what sources to gather. Mitigated by: TP asks clarifying questions.
