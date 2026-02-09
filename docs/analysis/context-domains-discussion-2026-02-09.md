# Context Domains Architecture Discussion

> **Date**: 2026-02-09
> **Participants**: Kevin Kim, Claude
> **Outcome**: ADR-034 Emergent Context Domains
> **Duration**: Extended first-principles analysis session

---

## Executive Summary

This document captures the full analytical journey that led to ADR-034: Emergent Context Domains. The discussion started with a tactical problem (all imported context going to "Personal") but evolved into a fundamental reexamination of YARNNN's context architecture.

**Key insight discovered**: Context domains should not be declared upfront by users, nor should they be inferred by AI classification. Instead, they should **emerge naturally from the patterns of deliverable source selection**. This approach resolves a multi-variant problem that previous approaches could not solve.

---

## Part 1: The Initial Problem

### Observed Behavior

Kevin noticed that context extraction from integrations (Slack, Gmail, Notion) was routing all content to "Personal" instead of being classified into projects. Screenshot showed the Context view with all items in Personal, regardless of source.

### Initial Hypothesis

The team had existing ADRs (ADR-024, ADR-030, ADR-032) that described a vision where:
- Contract extraction from TPs, files, and MCPs would classify content
- Classification would determine the project (context basket) before extraction
- This appeared to not be implemented

### Audit Findings

Investigation revealed:
1. `project_id` is optional in import requests (line 859 in integrations.py)
2. When `project_id` is None, memories become user-scoped (Personal)
3. No classification logic exists in the import pipeline
4. ADR-024's `suggest_project_for_memory` was designed for conversations, not imports

**Root cause**: The infrastructure assumed someone would specify where context goes, but no one did.

---

## Part 2: Initial Solution Attempts

### Attempt 1: Context Baskets (Explicit Definition)

**Proposal**: Rename "Projects" to "Context Baskets" with user-defined boundaries.

```
User defines baskets:
├── "Acme Corp" basket
├── "Advisory - BigCo" basket
└── "Personal" basket

User maps resources to baskets:
├── #engineering → Acme Corp
├── #client-bigco → BigCo
└── kevin@gmail.com → Personal
```

**Kevin's pushback**: This requires significant upfront setup. The mapping is explicit but cumbersome.

### Attempt 2: Platform-Workspace as Basket

**Proposal**: Basket = workspace level (organizational boundary), not topic level.

```
Slack workspace "Acme Corp" → Acme basket (all channels)
Notion workspace "Acme Corp" → same basket
Gmail kevin@acme.com → same basket (filtered)
```

**Rationale**: Platform structures already define organizational boundaries. One integration per platform per basket.

**Kevin's pushback**: This assumes platform organization is clean. What about agencies with multiple clients in one Slack? What about mixed personal/work email?

---

## Part 3: The Critical Realization

### Kevin's Key Question

> "Is the assumption that users in existing workspaces, emails, platforms in general actually have safe context domains separated? I assume mostly yes, but agencies and multi-vendor places will use same email for multiple contexts..."

This reframed the entire problem.

### The Real-World Spectrum

| User Type | Platform Reality | Challenge |
|-----------|-----------------|-----------|
| Single-org employee | Clean separation | Happy path |
| Agency employee | One Slack with multiple client channels | Workspace ≠ context domain |
| Consultant | Guest access to multiple client workspaces | Multiple workspaces (clean) |
| Mixed personal/work | Personal Gmail for side projects | Account ≠ context domain |

**Insight**: We cannot rely on platform structure to define context boundaries. Platform organization is messy in the real world.

### The Multi-Variant Problem

The challenge is to satisfy simultaneously:

1. **Clean case**: User with separate workspaces per context (easy)
2. **Mixed case**: User with multiple contexts in one workspace (hard)
3. **Low friction**: No heavy upfront setup (essential for adoption)
4. **Strong boundaries**: Prevent context bleed like ChatGPT (essential for trust)
5. **Accumulated knowledge**: Context grows and remains useful over time

Previous approaches solved some but not all:

| Approach | Clean Case | Mixed Case | Low Friction | Strong Boundaries | Accumulated Knowledge |
|----------|------------|------------|--------------|-------------------|----------------------|
| Current (no routing) | ❌ | ❌ | ✅ | ❌ | ❌ |
| Explicit baskets | ✅ | ✅ | ❌ | ✅ | ✅ |
| Workspace = basket | ✅ | ❌ | ✅ | ⚠️ | ✅ |
| AI classification | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ |

---

## Part 4: The Deliverable-First Pivot

### Reframing the Core Value

Kevin asked us to step back and consider: **What creates trust, reliability, and stickiness?**

This led to a crucial reframe:

> YARNNN isn't a context management system. It's a **deliverable production system** that uses context.

Users don't wake up thinking "I need to organize my context." They think "I need my weekly status update written and sent."

**Context organization is in service of deliverable quality, not an end in itself.**

### The Setup Burden Problem

```
OLD MENTAL MODEL:
Organize context → then create deliverables

PROBLEM:
- Users must do taxonomy work before getting value
- Friction at onboarding = abandonment
- "Why do I have to do all this setup?"

NEW MENTAL MODEL:
Create deliverables → context organization follows
```

### Initial Deliverable-Centric Proposal

**Proposal**: Each deliverable defines its own sources. No global context organization.

```
Deliverable: "Weekly Status to Sarah"
├── Destination: sarah@acme.com
├── Sources: #engineering, #product, sarah@ emails
└── Accumulated context: scoped to THIS deliverable only
```

**Kevin's pushback**: This drops context boundaries entirely. We'd have the same problem as ChatGPT - when user talks to TP, everything bleeds together.

---

## Part 5: The Synthesis - Emergent Domains

### The Key Insight

What if boundaries aren't **declared upfront** (setup burden) or **inferred by AI** (unreliable), but **emerge from deliverable patterns**?

```
USER CREATES DELIVERABLES:

Deliverable 1: "Weekly Status to Sarah"
  Sources: #engineering, #product

Deliverable 2: "Acme Project Update"
  Sources: #client-acme, #engineering

Deliverable 3: "BigCo Advisory Report"
  Sources: #client-bigco, bigco@

YARNNN OBSERVES:

Deliverables 1 & 2 share #engineering → same domain
Deliverable 3 has distinct sources → different domain

DOMAINS EMERGE:

Domain A: {#engineering, #product, #client-acme} ← "Acme Work"
Domain B: {#client-bigco, bigco@} ← "BigCo Advisory"
```

### Why This Solves the Multi-Variant Problem

| Requirement | How Emergent Domains Solve It |
|-------------|------------------------------|
| **Clean case** | All deliverables use same sources → one domain emerges |
| **Mixed case** | Different deliverables can use different channels from same workspace → multiple domains emerge |
| **Low friction** | User creates deliverables (valuable action), domains emerge automatically |
| **Strong boundaries** | Domains are implicit boundaries, TP retrieves from active domain only |
| **Accumulated knowledge** | Context accumulates within domains, shared across related deliverables |

### Kevin's Response

> "This is it. You've solved the multi-variant problem."

---

## Part 6: Key Design Decisions

### 1. Integrations Belong to User, Not Domains

```
PREVIOUS THINKING:
Basket owns integrations (1 Slack per basket)

FINAL DECISION:
User owns integrations
Domains are computed from source patterns
Same Slack workspace can feed multiple domains (different channels)
```

This handles the agency case where one Slack workspace serves multiple clients.

### 2. Domains Are System-Managed, User-Adjustable

```
DEFAULT BEHAVIOR:
- Domains are computed automatically
- Named automatically based on source patterns
- User never has to think about them

OPTIONAL POWER USER FEATURE:
- User can rename domains
- User can view domain composition
- User can manually adjust if auto-inference is wrong
```

### 3. Context Accumulates Within Domains

```
PREVIOUS THINKING (project_id model):
- project_id = NULL means "user-scoped, portable"
- project_id = UUID means "project-scoped"

FINAL DECISION:
- User Profile = portable identity/preferences (always available)
- Domain Context = accumulated knowledge from domain sources
- Context is shared across deliverables in same domain
```

### 4. TP Conversations Are Domain-Scoped

```
PRIORITY ORDER FOR DETERMINING ACTIVE DOMAIN:
1. Deliverable-anchored (viewing a deliverable → use its domain)
2. Explicit selection (user chose a domain)
3. Inferred from conversation (mentions sources/names)
4. Ambiguous → ask user

THIS PREVENTS CHATGPT PROBLEM:
- User asks about "database decision"
- In Acme domain → retrieves Acme context
- In BigCo domain → retrieves BigCo context (or says "not found")
- No bleed between domains
```

### 5. Style Learning Is Per-Domain

```
PREVIOUS THINKING:
"Personal style" extracted globally

FINAL DECISION:
Style is learned per domain:
- Acme domain → Acme communication style
- BigCo domain → BigCo communication style

Applied to deliverables in that domain automatically.
```

---

## Part 7: What We Didn't Do (And Why)

### Didn't: Require Upfront Basket/Domain Definition

**Why not**: Setup burden kills adoption. Users want value, not taxonomy design.

### Didn't: Use AI Classification for Routing

**Why not**: AI classification can drift, be wrong, creates black box. Manual cleanup is frustrating.

### Didn't: Make Domains First-Class User Objects

**Why not**: Domains are an implementation detail that enables good context scoping. Users care about deliverables, not domains. Making domains prominent would recreate the setup burden problem.

### Didn't: Drop Boundaries Entirely

**Why not**: Would recreate the ChatGPT problem where everything bleeds together. Trust requires boundaries.

### Didn't: Tie Integrations to Domains

**Why not**: Real-world platform organization is messy. Same workspace often contains multiple context domains. Tying integration to domain would force the "clean platform" assumption.

---

## Part 8: Remaining Questions

### Addressed in ADR but Deferred for Implementation

1. **Domain merging**: User wants to combine two auto-inferred domains
2. **Domain splitting**: One domain becomes too broad
3. **Cross-domain deliverables**: Pulling from multiple domains
4. **Shared domains**: Team/multi-user scenarios

### Philosophical Questions Surfaced

1. **What is "personal" context?**
   - User Profile (portable identity) is distinct from
   - Personal Life domain (personal integrations, personal projects)
   - These were conflated in original `project_id = NULL` model

2. **How granular should domains get?**
   - Current model: domains emerge from deliverable overlap
   - Could get very granular if user has many non-overlapping deliverables
   - May need clustering/merging heuristics

3. **What about users with no deliverables yet?**
   - Onboarding should push toward first deliverable
   - Before deliverables, context has no domain (or default domain)
   - Domain value materializes as user creates deliverables

---

## Part 9: Implementation Implications

### Schema Changes Required

1. New `context_domains` table (system-managed)
2. New `domain_sources` table (maps sources to domains)
3. New `deliverable_domains` table (links deliverables to computed domains)
4. Add `domain_id` to `memories` table
5. New `domain_style_profiles` table
6. Deprecate or repurpose `projects` table

### Algorithm Required

Domain inference via connected components:
- Build graph of sources that appear together in deliverables
- Find connected components
- Each component = one domain
- Recompute on deliverable create/update

### UX Changes Required

1. Deliverable creation becomes primary onboarding flow
2. Domain management is optional/settings
3. TP shows domain context indicator
4. Context browser can filter by domain

---

## Part 10: Lessons Learned

### On First-Principles Thinking

Starting from "how do we route imports correctly" led to incremental solutions. Stepping back to "what creates trust and value" led to the breakthrough.

### On Real-World Assumptions

Assuming platform organization is clean led to fragile solutions. Accepting that platforms are messy led to robust solutions.

### On User Mental Models

Users think about outcomes (deliverables), not infrastructure (context organization). Design should match mental models.

### On the Multi-Variant Problem

When requirements seem contradictory (low friction AND strong boundaries), the solution often involves a different axis entirely (emergent behavior rather than explicit definition).

---

## Appendix: Key Quotes from Discussion

> "Whatever will give me the maximum quality and trust and reliability of context management... is what I think should be a guiding criteria." - Kevin

> "Not every Figma account is perfect, not Gmail, nor Notion, not any platform. Purity in data and management is theoretical and not true in any scenario." - Kevin

> "YARNNN isn't a context management system. It's a deliverable production system that uses context." - Claude

> "Users don't wake up thinking 'I need to organize my context.' They think 'I need my weekly status update written and sent.'" - Claude

> "This is it. You've solved the multi-variant problem." - Kevin

---

## References

- [ADR-034: Emergent Context Domains](../adr/ADR-034-emergent-context-domains.md)
- [ADR-024: Context Classification Layer](../adr/ADR-024-context-classification-layer.md) (superseded approach)
- [ADR-005: Unified Memory with Embeddings](../adr/ADR-005-unified-memory-with-embeddings.md)
- [ADR-015: Unified Context Model](../adr/ADR-015-unified-context-model.md)
- [ADR-032: Platform-Native Frontend Architecture](../adr/ADR-032-platform-native-frontend-architecture.md)
