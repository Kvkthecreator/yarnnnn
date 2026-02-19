# ADR-034: Emergent Context Domains

> **Status**: Accepted
> **Created**: 2026-02-09
> **Decision**: Context domains emerge from deliverable source patterns, not upfront user definition
> **Related**: ADR-005 (Unified Memory), ADR-015 (Unified Context Model), ADR-024 (Context Classification), ADR-032 (Platform-Native Frontend)
> **Supersedes**: ADR-024 classification layer approach

---

## Context

### The Original Problem

Context extraction from integrations (Slack, Gmail, Notion) routes all imported content to "Personal" (user-scoped) by default. Investigation revealed:

1. `project_id` is optional in import requests
2. No classification logic determines where context belongs
3. Users see all extracted context in one undifferentiated pool

### The Deeper Problem

Through extensive first-principles analysis, we identified a fundamental tension:

**ChatGPT/Claude Problem**: No context boundaries. Everything bleeds together. User discusses Acme, then BigCo, then personal matters—the model conflates them, gives wrong advice, loses track.

**Over-Structured Solution**: Requiring users to define "baskets" or "projects" upfront and manually map platform resources creates:
- High setup friction (users abandon before getting value)
- Maintenance burden (mappings become stale)
- Assumes platform organization is clean (it rarely is)

### The Real-World Complexity

Users' existing platform organization is messy:

| Scenario | Platform Reality | Challenge |
|----------|-----------------|-----------|
| **Agency employee** | One Slack workspace with multiple client channels | Single workspace ≠ single context domain |
| **Consultant** | Guest access to multiple client workspaces | Multiple workspaces = clean separation (rare happy path) |
| **Mixed personal/work** | Personal Gmail used for side projects | Single account ≠ single context domain |
| **Single-org employee** | One workspace, one email | Clean, but still has topic-level separation needs |

**Key insight**: We cannot rely on platform structure to define context boundaries. But we also cannot burden users with upfront taxonomy design.

---

## Decision

### Core Principle: Deliverables First, Domains Emerge

**Context domains are not declared upfront. They emerge from patterns in how users configure deliverable sources.**

```
USER BEHAVIOR                          SYSTEM INFERENCE
─────────────────────────────────────────────────────────────────────────

User creates deliverables:             YARNNN observes source patterns:

"Weekly Status to Sarah"
  Sources: #engineering, #product      ─┐
                                        ├─→ Domain A emerges (source overlap)
"Acme Project Update"                   │
  Sources: #client-acme, #engineering ─┘

"BigCo Advisory Report"                ─────→ Domain B emerges (distinct sources)
  Sources: #client-bigco, bigco@

                                       Domains are implicit boundaries.
                                       Context accumulates within domains.
                                       TP conversations are domain-scoped.
```

### The Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                USER                                      │
│                                                                          │
│  Portable Profile:                                                      │
│  ├── Identity (name, role)                                              │
│  ├── Base preferences (formatting, verbosity)                           │
│  └── Expertise (domains they know)                                      │
│                                                                          │
│  Always available. Applied to ALL deliverables regardless of domain.    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ owns
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PLATFORM INTEGRATIONS                               │
│                                                                          │
│  Connections to external platforms:                                     │
│  ├── Slack (workspace access)                                           │
│  ├── Gmail (account access)                                             │
│  ├── Notion (workspace access)                                          │
│  └── Calendar (account access)                                          │
│                                                                          │
│  Integrations belong to USER (not to domains).                          │
│  They provide ACCESS to resources. No routing logic here.               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ owns
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          DELIVERABLES                                    │
│                                                                          │
│  The PRIMARY user interaction. Each deliverable defines:                │
│  ├── Destination: where output goes (email, Slack channel, Notion page) │
│  ├── Sources: which resources feed it (explicit selection)              │
│  ├── Schedule: when it runs                                             │
│  └── Governance: review mode (draft/semi-auto/auto)                     │
│                                                                          │
│  Example:                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ "Weekly Status to Sarah"                                         │   │
│  │   Destination: sarah@acme.com                                    │   │
│  │   Sources: #engineering, #product, threads with sarah@           │   │
│  │   Schedule: Fridays 4pm                                          │   │
│  │   Governance: Draft (review before send)                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Users create deliverables to GET VALUE. This is the entry point.       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ YARNNN observes source patterns
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    EMERGENT CONTEXT DOMAINS                              │
│                                                                          │
│  System-inferred from deliverable source overlap:                       │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Domain: "Acme Work" (auto-named, user can rename)                │   │
│  │                                                                   │   │
│  │ Sources (union of related deliverables):                         │   │
│  │   #engineering, #product, #client-acme, sarah@, acme@            │   │
│  │                                                                   │   │
│  │ Deliverables in this domain:                                     │   │
│  │   - Weekly Status to Sarah                                       │   │
│  │   - Acme Project Update                                          │   │
│  │   - Engineering Digest                                           │   │
│  │                                                                   │   │
│  │ Accumulated context (scoped to this domain):                     │   │
│  │   - "Decided to use PostgreSQL for new service"                  │   │
│  │   - "Launch date moved to March 15"                              │   │
│  │   - "Sarah prefers bullet points with timeline detail"           │   │
│  │                                                                   │   │
│  │ Style profile (learned from this domain's sources):              │   │
│  │   - Communication patterns from sent emails to @acme.com         │   │
│  │   - Slack tone in #engineering                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Domain: "BigCo Advisory" (auto-named)                            │   │
│  │                                                                   │   │
│  │ Sources: #client-bigco, bigco@                                   │   │
│  │ Deliverables: BigCo Advisory Report                              │   │
│  │ Accumulated context: scoped to BigCo sources                     │   │
│  │ Style profile: learned from BigCo communications                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Domains are IMPLICIT BOUNDARIES that prevent context bleed.            │
│  Users don't have to define them. They emerge.                          │
│  Users CAN name/adjust them if desired (optional).                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. Deliverable Creation (User Action)

User creates a deliverable by specifying:
- **Destination**: Where the output goes
- **Sources**: Which platform resources inform it
- **Schedule**: When it runs

```
User: "I need a weekly update for my manager"

YARNNN: "Where should this go?"
User: sarah@acme.com

YARNNN: "What should inform this update?"
[Shows connected platforms and resources]
User selects: #engineering, #product, email threads with Sarah

YARNNN: "When should this run?"
User: Fridays at 4pm

→ Deliverable created. User gets value immediately.
```

### 2. Domain Inference (System Behavior)

YARNNN analyzes source overlap across deliverables:

```python
# Pseudo-algorithm for domain inference

def infer_domains(user_deliverables):
    # Build source graph
    source_to_deliverables = {}
    for d in user_deliverables:
        for source in d.sources:
            source_to_deliverables[source].add(d)

    # Find connected components (sources that appear together)
    domains = []
    for component in find_connected_components(source_to_deliverables):
        domain = Domain(
            sources=component.sources,
            deliverables=component.deliverables,
            name=auto_generate_name(component)  # e.g., "Acme Work"
        )
        domains.append(domain)

    return domains
```

**Source overlap creates implicit grouping**:
- Deliverable A uses: #engineering, #product
- Deliverable B uses: #engineering, #client-acme
- Overlap on #engineering → same domain

### 3. Context Accumulation (Scoped to Domains)

When context is extracted from sources, it's scoped to the domain containing those sources:

```
Import from #engineering:
  → Find domain containing #engineering
  → Store context with domain_id

Context: "Decided to use PostgreSQL for new service"
  → Scoped to "Acme Work" domain
  → Available to all deliverables in that domain
  → NOT available to BigCo deliverables
```

### 4. TP Conversations (Domain-Scoped)

When user converses with TP, context is pulled from the relevant domain:

**Domain determination** (in priority order):

1. **Deliverable-anchored**: User is viewing/editing a deliverable → use that deliverable's domain
2. **Explicit selection**: User has selected a domain context
3. **Inferred from conversation**: User mentions "Sarah" or "engineering" → infer domain
4. **Ask when ambiguous**: "Are you asking about Acme or BigCo?"

```
User (viewing "Weekly Status to Sarah"):
  "What did we decide about the database?"

TP retrieves from Acme Work domain:
  → "You decided to use PostgreSQL for the new service (discussed in #engineering, Feb 5)"

---

User (viewing "BigCo Advisory Report"):
  "What did we decide about the database?"

TP retrieves from BigCo domain:
  → "I don't see database decisions in your BigCo context.
     Did you mean to ask about Acme?"
```

**This prevents the ChatGPT problem** of context bleed across unrelated work.

### 5. Style Learning (Per-Domain)

Style is learned from each domain's sources and applied to that domain's deliverables:

```
Domain: "Acme Work"
  Style learned from:
    - Sent emails to @acme.com
    - Slack messages in #engineering, #product

  Style profile:
    - Casual tone in Slack
    - More formal in email to leadership
    - Uses bullet points
    - Includes timeline estimates

Domain: "BigCo Advisory"
  Style learned from:
    - Sent emails to @bigco.com
    - Slack messages in #client-bigco

  Style profile:
    - Very formal tone
    - Executive summary at top
    - Detailed appendices
```

Deliverables automatically use their domain's style profile.

---

## User Experience

### Onboarding Flow

```
STEP 1: Connect platforms
─────────────────────────────────────────────────────────────────────────
"Connect your work tools"
[Connect Slack] [Connect Gmail] [Connect Notion]

→ Integrations created at user level
→ No domain/basket configuration needed

STEP 2: Create first deliverable
─────────────────────────────────────────────────────────────────────────
"What do you need YARNNN to produce for you?"

→ "Weekly status update for my manager"

"Where should this go?"
→ sarah@acme.com

"What should inform it?" [Select from connected sources]
→ #engineering, #product

"When?"
→ Fridays at 4pm

DONE. First deliverable created. First domain emerges implicitly.

STEP 3: Create more deliverables (ongoing)
─────────────────────────────────────────────────────────────────────────
Each new deliverable either:
  - Joins an existing domain (source overlap)
  - Creates a new domain (distinct sources)

User never explicitly manages domains unless they want to.
```

### Time to Value

| Approach | Steps to First Value | User Burden |
|----------|---------------------|-------------|
| **Basket-first** | Connect → Create baskets → Map resources → Create deliverable | High |
| **Deliverable-first (no domains)** | Connect → Create deliverable | Low, but context bleeds |
| **Emergent domains** | Connect → Create deliverable | Low, AND context is bounded |

### Optional Domain Management

Users CAN manage domains if they want (power user feature):

```
Settings → Context Domains

┌─────────────────────────────────────────────────────────────────────────┐
│ Your Context Domains (auto-managed)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ● Acme Work                                               [Rename]      │
│   Sources: #engineering, #product, #client-acme, sarah@, acme@          │
│   Deliverables: 3                                                       │
│   Context items: 847                                                    │
│                                                                          │
│ ● BigCo Advisory                                          [Rename]      │
│   Sources: #client-bigco, bigco@                                        │
│   Deliverables: 1                                                       │
│   Context items: 124                                                    │
│                                                                          │
│ ● Uncategorized                                                         │
│   Sources not yet in any deliverable                                    │
│                                                                          │
│ [+ Create manual domain]  ← For power users who want explicit control   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Schema Changes

```sql
-- New: Context domains (system-managed, user-adjustable)
CREATE TABLE context_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Domain identity
    name TEXT NOT NULL,                      -- Auto-generated or user-set
    name_source TEXT DEFAULT 'auto',         -- 'auto' or 'user'

    -- Domain metadata
    is_default BOOLEAN DEFAULT false,        -- For "Uncategorized" domain

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Source-to-domain mapping (computed from deliverable sources)
CREATE TABLE domain_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES context_domains(id) ON DELETE CASCADE,

    -- Source identification
    provider TEXT NOT NULL,                  -- slack, gmail, notion
    resource_id TEXT NOT NULL,               -- Channel ID, label, page ID
    resource_name TEXT,                      -- Human-readable name

    -- How this mapping was established
    source_type TEXT DEFAULT 'inferred',     -- 'inferred' or 'manual'

    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(domain_id, provider, resource_id)
);

-- Deliverable-to-domain relationship (computed, not user-managed)
CREATE TABLE deliverable_domains (
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    domain_id UUID NOT NULL REFERENCES context_domains(id) ON DELETE CASCADE,

    PRIMARY KEY (deliverable_id, domain_id)
);

-- Memories now reference domains instead of projects
ALTER TABLE memories ADD COLUMN domain_id UUID REFERENCES context_domains(id);

-- Index for domain-scoped retrieval
CREATE INDEX idx_memories_domain ON memories(domain_id) WHERE is_active = true;

-- Style profiles per domain
CREATE TABLE domain_style_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES context_domains(id) ON DELETE CASCADE,

    -- Platform-specific styles
    platform TEXT NOT NULL,                  -- slack, gmail, notion
    style_attributes JSONB DEFAULT '{}',     -- Learned style characteristics

    -- Training data reference
    sample_count INTEGER DEFAULT 0,
    last_trained_at TIMESTAMPTZ,

    UNIQUE(domain_id, platform)
);
```

### Migration from Current Schema

```sql
-- Phase 1: Create default domain for each user's existing content
INSERT INTO context_domains (user_id, name, is_default)
SELECT DISTINCT user_id, 'Default', true
FROM memories
WHERE domain_id IS NULL;

-- Phase 2: Assign existing memories to default domain
UPDATE memories m
SET domain_id = (
    SELECT id FROM context_domains cd
    WHERE cd.user_id = m.user_id AND cd.is_default = true
)
WHERE m.domain_id IS NULL;

-- Phase 3: Existing projects become deliverable groupings (optional)
-- Projects table can be deprecated or repurposed for UI organization
```

---

## Domain Inference Algorithm

### Source Overlap Detection

```python
from collections import defaultdict
from typing import Set, List

def compute_domains(deliverables: List[Deliverable]) -> List[Domain]:
    """
    Compute context domains from deliverable source patterns.

    Uses connected components algorithm:
    - Sources that appear together in ANY deliverable are connected
    - Connected components become domains
    """

    # Build adjacency: which sources appear together?
    source_connections = defaultdict(set)

    for deliverable in deliverables:
        sources = set(deliverable.sources)
        for source in sources:
            # Each source is connected to all other sources in same deliverable
            source_connections[source].update(sources - {source})

    # Find connected components
    visited = set()
    domains = []

    for source in source_connections:
        if source not in visited:
            # BFS to find all connected sources
            component_sources = set()
            queue = [source]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component_sources.add(current)
                queue.extend(source_connections[current] - visited)

            # Create domain from component
            component_deliverables = [
                d for d in deliverables
                if set(d.sources) & component_sources
            ]

            domain = Domain(
                sources=component_sources,
                deliverables=component_deliverables,
                name=generate_domain_name(component_sources, component_deliverables)
            )
            domains.append(domain)

    return domains


def generate_domain_name(sources: Set[str], deliverables: List[Deliverable]) -> str:
    """
    Auto-generate a domain name from its sources/deliverables.

    Heuristics:
    1. If all sources share a common prefix (e.g., "#client-acme", "acme@")
       → Use that prefix ("Acme")
    2. If deliverables have common theme in titles
       → Use that theme
    3. Fallback: Use most common source name
    """
    # Extract potential names from sources
    # e.g., "#client-acme" → "Acme", "acme@company.com" → "Acme"

    # Implementation details...
    pass
```

### Incremental Updates

When a deliverable is created/updated:

```python
async def on_deliverable_change(deliverable: Deliverable, user_id: str):
    """Recompute domains when deliverable sources change."""

    # Get all user's deliverables
    all_deliverables = await get_user_deliverables(user_id)

    # Recompute domains
    new_domains = compute_domains(all_deliverables)

    # Diff against existing domains
    existing_domains = await get_user_domains(user_id)

    # Apply changes (create new, merge overlapping, preserve user renames)
    await reconcile_domains(existing_domains, new_domains, user_id)
```

---

## TP Context Scoping

### Determining Active Domain

```python
async def get_active_domain(
    user_id: str,
    conversation_context: ConversationContext
) -> Optional[Domain]:
    """
    Determine which domain should scope the current TP conversation.

    Priority:
    1. Explicit user selection (if user chose a domain)
    2. Active deliverable (if viewing/editing one)
    3. Conversation inference (mentions, entities)
    4. Ambiguous → ask user
    """

    # 1. Explicit selection
    if conversation_context.explicit_domain_id:
        return await get_domain(conversation_context.explicit_domain_id)

    # 2. Active deliverable
    if conversation_context.active_deliverable_id:
        return await get_deliverable_domain(conversation_context.active_deliverable_id)

    # 3. Conversation inference
    domains = await get_user_domains(user_id)

    if len(domains) == 1:
        return domains[0]  # Only one domain, use it

    # Check for mentions that map to domain sources
    mentioned_sources = extract_source_mentions(conversation_context.messages)
    for domain in domains:
        if mentioned_sources & domain.sources:
            return domain  # Mentioned source belongs to this domain

    # 4. Ambiguous
    return None  # TP should ask user for clarification
```

### Memory Retrieval with Domain Scoping

```python
async def retrieve_context(
    user_id: str,
    query: str,
    domain_id: Optional[str] = None
) -> List[Memory]:
    """
    Retrieve relevant memories, scoped to domain if specified.
    """

    # Always include user profile (portable)
    profile_context = await get_user_profile(user_id)

    # Domain-scoped retrieval
    if domain_id:
        memories = await search_memories(
            user_id=user_id,
            query=query,
            domain_id=domain_id  # Scope to domain
        )
    else:
        # No domain specified - search across all (with lower confidence)
        memories = await search_memories(
            user_id=user_id,
            query=query,
            domain_id=None
        )

    return profile_context + memories
```

---

## Preventing Context Bleed

### The ChatGPT Problem

```
WITHOUT DOMAINS (ChatGPT-style):

User: "What did we decide about the database?"

System searches ALL context:
  → "Acme: Decided to use PostgreSQL"
  → "BigCo: Discussed MongoDB migration"
  → "Personal: Looking at SQLite for side project"

System returns mixed results:
  → User gets confused
  → Wrong context influences response
  → Trust erodes
```

### The YARNNN Solution

```
WITH EMERGENT DOMAINS:

User (in Acme domain context): "What did we decide about the database?"

System searches ONLY Acme domain:
  → "Decided to use PostgreSQL for new service"

Clear, relevant, bounded response.

---

User (in BigCo domain context): "What did we decide about the database?"

System searches ONLY BigCo domain:
  → "No database decisions found in BigCo context.
     Did you mean to ask about Acme?"

Boundary prevents incorrect context from surfacing.
```

---

## Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Time to first deliverable** | < 5 minutes | Low friction onboarding |
| **Deliverables with working context** | > 90% | Emergent domains capture relevant sources |
| **Context bleed incidents** | < 5% | Domains effectively prevent mixing |
| **User domain adjustments** | < 20% | Auto-inference is good enough |
| **TP context relevance** | > 85% | Domain scoping improves retrieval |

---

## Migration & Rollout

### Phase 1: Schema & Infrastructure

1. Create `context_domains`, `domain_sources`, `deliverable_domains` tables
2. Implement domain inference algorithm
3. Add `domain_id` to memories table
4. Create default domain for existing users

### Phase 2: Deliverable Integration

1. Update deliverable creation to trigger domain recomputation
2. Link deliverables to computed domains
3. Update context retrieval to be domain-scoped

### Phase 3: TP Integration

1. Implement active domain detection
2. Update TP context assembly to use domain scoping
3. Add domain clarification flow for ambiguous cases

### Phase 4: UI Updates

1. Add optional domain management UI (Settings)
2. Show domain indicator in TP conversations
3. Add domain context to deliverable detail views

### Phase 5: Style Integration

1. Implement per-domain style learning
2. Apply domain style to deliverable generation
3. UI for viewing/adjusting style profiles

---

## Open Questions (Deferred)

1. **Domain merging**: What if user wants to merge two auto-inferred domains?
   - Support manual merge in settings
   - System remembers merge preference

2. **Domain splitting**: What if one domain becomes too broad?
   - Detect based on source count threshold
   - Suggest split to user

3. **Cross-domain deliverables**: Can a deliverable pull from multiple domains?
   - Start with: No, one domain per deliverable
   - Future: Allow with explicit user consent

4. **Shared domains**: Can domains be shared between users (teams)?
   - Defer to post-launch
   - Current model is single-user

---

## Conclusion

Emergent Context Domains solve the fundamental tension between:
- **Structure** (preventing ChatGPT-style context soup)
- **Flexibility** (not burdening users with upfront taxonomy)

**Key insights**:
1. Users define deliverables to get value (primary interaction)
2. Domains emerge from deliverable source patterns (no setup burden)
3. Domains create implicit boundaries (context stays relevant)
4. Users can adjust if needed (optional control)

**The result**: Low-friction onboarding, bounded context, accumulated knowledge, and trustworthy deliverables.

---

## Implementation Status

> **Implementation Date**: 2026-02-09
> **Status**: Phases 1-3 Complete, Context v2 Migration Complete

### Completed

#### Phase 1: Schema & Infrastructure
- [x] Migration 034: `context_domains`, `domain_sources`, `deliverable_domains`, `domain_style_profiles` tables
- [x] `domain_id` column added to `memories` table
- [x] Helper functions: `get_or_create_default_domain`, `find_domain_for_source`, `get_deliverable_domain`
- [x] Default domain created for existing users via migration

#### Phase 2: Deliverable Integration
- [x] Domain inference service (`api/services/domain_inference.py`)
- [x] Connected components algorithm for source overlap detection
- [x] Domain recomputation trigger on deliverable creation/update (`api/routes/deliverables.py`)
- [x] Import flow updated to route memories to domains (`api/jobs/import_jobs.py`)

#### Phase 3: TP Integration
- [x] Migration 035: `search_memories` updated for domain_id scoping
- [x] New `get_memories_by_importance` function for non-semantic fallback
- [x] `Memory` and `ContextBundle` refactored to use `domain_id` (`api/agents/base.py`)
- [x] `load_memories` function updated for domain scoping (`api/routes/chat.py`)
- [x] Active domain detection from surface context (deliverable being viewed)
- [x] Extraction service updated to route to domains (`api/services/extraction.py` — deleted in ADR-064, replaced by `api/services/memory.py`)

### Remaining

#### Phase 4: UI Updates (Partial)
- [x] Context v2: ContextBrowserSurface rewritten for domain-based browsing
- [x] Context v2: DomainSelector replaces ProjectSelector
- [ ] Domain management UI in Settings (power user feature)
- [ ] Domain indicator in TP conversations
- [ ] Domain context display in deliverable views

#### Phase 5: Style Integration
- [ ] Per-domain style learning implementation
- [ ] Style profile application in deliverable generation
- [ ] Style profile UI

### Key Files Modified

| File | Changes |
|------|---------|
| `supabase/migrations/034_emergent_context_domains.sql` | Schema for domains, sources, deliverable mapping |
| `supabase/migrations/035_domain_scoped_search.sql` | Updated search functions for domain scoping |
| `api/services/domain_inference.py` | Domain inference algorithm and reconciliation |
| `api/jobs/import_jobs.py` | Memory routing to domains during import |
| `api/routes/deliverables.py` | Domain recomputation on deliverable changes |
| `api/routes/chat.py` | Domain-scoped context loading in TP |
| `api/agents/base.py` | Memory/ContextBundle now use domain_id |
| `api/services/memory.py` | Unified Memory Service (replaced `extraction.py` per ADR-064) |

### Migration Notes

- Existing users automatically receive a default domain via migration
- Legacy `project_id` on memories is deprecated but preserved for backwards compatibility
- Domain inference runs on deliverable creation/update - existing deliverables need manual trigger
- Style profiles table created but learning not yet implemented

---

## Addendum: Context v2 Migration (Project → Domain Swap)

> **Added**: 2026-02-09
> **Completed**: 2026-02-09
> **Status**: ✅ Complete

### Rationale

After implementing Phases 1-3, a hybrid state emerged where both `project_id` and `domain_id` coexist. This creates:
- Duplicated API surface (`/api/context/*` and `/api/domains/*`)
- Confusion about which scoping mechanism to use
- Frontend components using inconsistent patterns

**Decision**: Treat domains as "Context v2" - a complete replacement, not an addition.

### Migration Plan (Completed)

#### Step 1: Deprecate `/api/context/*` project-scoped routes ✅

**Routes migrated:**

| Current Route | Action | New Route |
|---------------|--------|-----------|
| `GET /api/context/user/memories` | Keep | (maps to default domain) |
| `POST /api/context/user/memories` | Keep | (creates in default domain) |
| `GET /api/context/projects/{id}/memories` | **Deprecated** | `GET /api/domains/{id}/memories` |
| `POST /api/context/projects/{id}/memories` | **Deprecated** | `POST /api/domains/{id}/memories` |
| `GET /api/context/projects/{id}/context` | **Deprecated** | `GET /api/domains/{id}` |
| `POST /api/context/projects/{id}/memories/import` | **Deprecated** | Use import job with domain routing |

Project-scoped routes marked deprecated in `api/routes/context.py`.

#### Step 2: Add domain memory routes ✅

Added to `api/routes/domains.py`:
- `GET /api/domains/{domain_id}/memories` - List domain memories
- `POST /api/domains/{domain_id}/memories` - Create domain memory

#### Step 3: Migrate ContextBrowserSurface ✅

Replaced project-based browsing with domain-based:
- ~~`ProjectSelector` component~~ → Removed
- Added `DomainSelector` component (inline in ContextBrowserSurface)
- Uses `domain_id` for memory fetching via `api.domains.memories.list()`

#### Step 4: Remove ProjectContext ✅

Deleted `web/contexts/ProjectContext.tsx`:
- Active domain comes from surface context (via `useActiveDomain`)
- Removed `ProjectSelector.tsx` component

#### Step 5: Update API client ✅

Updated `web/lib/api/client.ts`:
- Added `domains.memories.list(domainId)`
- Added `domains.memories.create(domainId, data)`
- `userMemories` still maps to default domain

#### Step 6: Update frontend hooks ✅

Updated `web/hooks/useMemories.ts`:
- Added `useDomainMemories(domainId)` hook
- `useUserMemories` still works for default domain context

#### Step 7: Fix type definitions ✅

Updated scope types from `'project'` to `'domain'`:
- `web/types/desk.ts`: DeskSurface context-browser scope type
- `web/lib/tp-chips.ts`: ContextScope type and getContextScope function
- `web/components/surfaces/ProjectDetailSurface.tsx`: Navigate to user scope instead of project

### Files Modified

| File | Changes | Status |
|------|---------|--------|
| `api/routes/context.py` | Marked project-scoped routes as deprecated | ✅ |
| `api/routes/domains.py` | Added memory routes | ✅ |
| `api/services/extraction.py` | Added `domain_id` parameter to `create_memory_manual` | ✅ |
| `web/lib/api/client.ts` | Added `domains.memories` methods | ✅ |
| `web/hooks/useMemories.ts` | Added `useDomainMemories` hook | ✅ |
| `web/components/surfaces/ContextBrowserSurface.tsx` | Rewrote for domain-based browsing | ✅ |
| `web/types/desk.ts` | Updated scope type `'project'` → `'domain'` | ✅ |
| `web/lib/tp-chips.ts` | Updated ContextScope type for domains | ✅ |
| `web/components/surfaces/ProjectDetailSurface.tsx` | Updated context link to user scope | ✅ |

### Files Deleted

| File | Reason | Status |
|------|--------|--------|
| `web/contexts/ProjectContext.tsx` | Replaced by domain context via `useActiveDomain` | ✅ |
| `web/components/shell/ProjectSelector.tsx` | Replaced by DomainSelector in ContextBrowserSurface | ✅ |

### Backwards Compatibility

- Keep `project_id` column in `memories` table temporarily
- Existing memories with `project_id` but no `domain_id` will be assigned to default domain
- API returns 410 Gone for deprecated routes after transition period

---

## References

- [ADR-005: Unified Memory with Embeddings](./ADR-005-unified-memory-with-embeddings.md)
- [ADR-015: Unified Context Model](./ADR-015-unified-context-model.md)
- [ADR-024: Context Classification Layer](./ADR-024-context-classification-layer.md) (superseded)
- [ADR-032: Platform-Native Frontend Architecture](./ADR-032-platform-native-frontend-architecture.md)
- [Discussion: Context Extraction Audit 2026-02-09](../analysis/context-domains-discussion-2026-02-09.md)
