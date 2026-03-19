# ADR-122: Project Type Registry — Unified Scaffolding Layer

**Status**: Phases 1-3 Implemented
**Date**: 2026-03-19
**Supersedes**: ADR-110 (Onboarding Bootstrap) — bootstrap becomes a consumer of the registry, not a standalone creation path
**Extends**: ADR-119 (Workspace Filesystem), ADR-120 (Project Execution & Work Budget), ADR-121 (PM Intelligence Director)
**Interacts with**: ADR-111 (Composer), ADR-118 (Skills as Capability Layer)

## Context

YARNNN has two agent creation paths that produce structurally identical agents through different machinery:

1. **Bootstrap path** (`onboarding_bootstrap.py`): OAuth connect → `BOOTSTRAP_TEMPLATES` dict → `create_agent_record()` → standalone platform digest agent with `origin="system_bootstrap"`.
2. **Composer path** (`composer.py`): Heartbeat assessment → LLM decision → `_execute_create_project()` → project with PM + contributor agents via `handle_create_project()`.

The bootstrap path creates agents *before an objective exists*. A "Slack Recap" agent exists because Slack was connected, not because the user wants a daily team pulse. This breaks the mental model: every other agent exists to serve a project goal.

Meanwhile, `PLATFORM_DIGEST_TITLES` in `composer.py` duplicates `BOOTSTRAP_TEMPLATES` in `onboarding_bootstrap.py`. The Composer's gap-filling logic (`_create_digest_for_platform()`) creates standalone agents — the same structural anomaly as bootstrap.

**The fix**: A single Project Type Registry that all creation paths consume. Bootstrap creates a *project* (from a platform type), not a standalone agent. Composer gap-filling creates a *project* (from the same registry), not a standalone agent. User/TP creation flows use the same registry for custom types.

## Decision

### 1. Project Type Registry

A curated, code-side registry of project type definitions. Each type fully specifies: objective, agents to scaffold, PM configuration, delivery defaults, and uniqueness constraints.

**Location**: `api/services/project_registry.py` — single source of truth.

**Why code-side, not a DB table**: Project types are curated platform decisions (like `ROLE_PORTFOLIOS`, `PLATFORM_REGISTRY`, `SKILL_ENABLED_ROLES`). They change at deploy time, not runtime. A DB table adds migration overhead and query latency for a catalog of ~10-15 entries that the product team controls. Follows the existing registry pattern.

```python
# api/services/project_registry.py
# Project Type Registry v1.0 — ADR-122
# Changelog: api/prompts/CHANGELOG.md

from typing import Optional

PROJECT_TYPE_REGISTRY: dict[str, dict] = {

    # ── Platform digest types (1:1 with platform, uniqueness enforced) ──

    "slack_digest": {
        "display_name": "Slack Recap",
        "category": "platform",
        "platform": "slack",                    # Uniqueness key: 1 per platform per user
        "description": "Daily recap of Slack activity across connected channels.",
        "objective": {
            "deliverable": "Daily Slack recap",
            "audience": "You",
            "format": "email",
            "purpose": "Stay informed on team activity without reading every message",
        },
        "agents": [
            {
                "title_template": "Slack Recap",
                "role": "digest",
                "scope": "platform",
                "frequency": "daily",
                "sources_from": "platform",     # Auto-populated from platform_connections
            },
        ],
        "pm": False,                            # Single-agent project, no PM needed
        "assembly_spec": None,                  # No assembly — agent output IS the deliverable
        "delivery_default": {"platform": "email"},
        "version": "2026-03-19",
    },

    "gmail_digest": {
        "display_name": "Gmail Digest",
        "category": "platform",
        "platform": "google",
        "description": "Daily digest of Gmail activity across connected labels.",
        "objective": {
            "deliverable": "Daily Gmail digest",
            "audience": "You",
            "format": "email",
            "purpose": "Inbox triage — highlights and action items surfaced daily",
        },
        "agents": [
            {
                "title_template": "Gmail Digest",
                "role": "digest",
                "scope": "platform",
                "frequency": "daily",
                "sources_from": "platform",
            },
        ],
        "pm": False,
        "assembly_spec": None,
        "delivery_default": {"platform": "email"},
        "version": "2026-03-19",
    },

    "notion_digest": {
        "display_name": "Notion Summary",
        "category": "platform",
        "platform": "notion",
        "description": "Daily summary of Notion activity across connected pages.",
        "objective": {
            "deliverable": "Daily Notion summary",
            "audience": "You",
            "format": "email",
            "purpose": "Track workspace changes without visiting every page",
        },
        "agents": [
            {
                "title_template": "Notion Summary",
                "role": "digest",
                "scope": "platform",
                "frequency": "daily",
                "sources_from": "platform",
            },
        ],
        "pm": False,
        "assembly_spec": None,
        "delivery_default": {"platform": "email"},
        "version": "2026-03-19",
    },

    # ── Multi-agent project types (Composer / user created) ──

    "cross_platform_synthesis": {
        "display_name": "Cross-Platform Insights",
        "category": "synthesis",
        "platform": None,                       # No uniqueness constraint
        "description": "Weekly synthesis across multiple platforms — patterns, themes, action items.",
        "objective": {
            "deliverable": "Weekly cross-platform insights report",
            "audience": "You",
            "format": "pdf",
            "purpose": "See patterns across platforms that individual digests miss",
        },
        "agents": [
            {
                "title_template": "Cross-Platform Synthesizer",
                "role": "synthesize",
                "scope": "cross_platform",
                "frequency": "weekly",
                "sources_from": "all_platforms",
            },
        ],
        "pm": True,                             # PM coordinates assembly timing
        "assembly_spec": "Synthesize themes across all contributor outputs into a cohesive report.",
        "delivery_default": {"platform": "email"},
        "version": "2026-03-19",
    },

    "custom": {
        "display_name": "Custom Project",
        "category": "custom",
        "platform": None,
        "description": "User-defined project with custom agents and delivery.",
        "objective": None,                      # User provides
        "agents": [],                           # User/Composer specifies
        "pm": True,                             # Default PM for multi-agent
        "assembly_spec": None,                  # User provides
        "delivery_default": {"platform": "email"},
        "version": "2026-03-19",
    },
}
```

### 2. Registry Access Functions

```python
def get_project_type(type_key: str) -> Optional[dict]:
    """Look up a project type definition."""
    return PROJECT_TYPE_REGISTRY.get(type_key)

def get_platform_project_type(platform: str) -> Optional[tuple[str, dict]]:
    """Find the project type for a given platform (slack, google, notion)."""
    for key, ptype in PROJECT_TYPE_REGISTRY.items():
        if ptype.get("platform") == platform:
            return (key, ptype)
    return None

def list_project_types(category: Optional[str] = None) -> list[dict]:
    """List all project types, optionally filtered by category."""
    types = []
    for key, ptype in PROJECT_TYPE_REGISTRY.items():
        if category and ptype.get("category") != category:
            continue
        types.append({"key": key, **ptype})
    return types
```

### 3. Unified Scaffolding Function

A single `scaffold_project()` function replaces both `maybe_bootstrap_agent()` and `_create_digest_for_platform()`:

```python
async def scaffold_project(
    client,
    user_id: str,
    type_key: str,
    *,
    title_override: str | None = None,
    intent_override: dict | None = None,
    agents_override: list[dict] | None = None,
    contributors: list[str] | None = None,      # Existing agent slugs to add
    assembly_spec_override: str | None = None,
    delivery_override: dict | None = None,
    execute_now: bool = False,
) -> dict:
    """
    Scaffold a project from the registry.

    1. Look up type definition
    2. Enforce uniqueness (platform types: 1 per platform per user)
    3. Create project via ProjectWorkspace.write_project()
    4. Create agents from type.agents[] specs
    5. Optionally create PM agent (type.pm)
    6. Optionally execute first agent run (execute_now)
    7. Return {project_slug, agents_created, pm_agent_id}
    """
```

### 4. Platform Uniqueness Enforcement

For `category="platform"` types, uniqueness is enforced at scaffold time:

```python
# Check: does a project of this type already exist for this user?
existing = (
    db.table("workspace_files")
    .select("path")
    .eq("user_id", user_id)
    .like("path", "/projects/%/PROJECT.md")
    .execute()
)
for row in (existing.data or []):
    project = ProjectWorkspace(client, user_id, slug).read_project()
    if project.get("type_key") == type_key:
        return {"success": False, "reason": "duplicate", "existing_slug": slug}
```

**`type_key` stored in PROJECT.md** — a new field in the project identity section. This is the uniqueness anchor.

Non-platform types have no uniqueness constraint. Users can create multiple custom projects.

### 5. PM for Single-Agent Projects

Platform digest projects have `pm: False`. The single digest agent's output IS the project deliverable — no assembly, no coordination overhead. This means:

- No PM agent created
- No assembly step
- Agent delivery goes directly to the project's delivery destination
- Work budget: 1 unit per run (same as today's standalone agent)

When the Composer's lifecycle expansion detects a senior digest agent and wants to create a synthesis project, it scaffolds a `cross_platform_synthesis` type which DOES have `pm: True`. The PM then coordinates the multi-agent assembly.

**Stress test**: A single-agent project without PM is functionally identical to today's standalone agent — same execution strategy, same delivery path, same work budget cost. The only difference is it lives under `/projects/{slug}/` instead of being a loose agent. This is the correct behavior: the project is the container, PM is optional coordination overhead added only when multi-agent assembly is needed.

### 6. Bootstrap Rewrite

`onboarding_bootstrap.py` becomes a thin caller of `scaffold_project()`:

```python
# BEFORE (ADR-110)
async def maybe_bootstrap_agent(client, user_id, platform):
    template = BOOTSTRAP_TEMPLATES.get(platform)
    # ... 150 lines of agent creation, idempotency, inline execution

# AFTER (ADR-122)
async def maybe_bootstrap_project(client, user_id, platform):
    type_info = get_platform_project_type(platform)
    if not type_info:
        return None
    type_key, ptype = type_info
    result = await scaffold_project(
        client, user_id, type_key,
        execute_now=True,
    )
    if not result["success"]:
        logger.info(f"[BOOTSTRAP] Skipped {type_key}: {result.get('reason')}")
        return None
    return result
```

Idempotency is handled by `scaffold_project()`'s uniqueness check, not by title-matching heuristics.

### 7. Composer Rewrite

Composer gap-filling and lifecycle expansion both consume the registry:

```python
# Gap-filling: BEFORE
platforms_without_digest = [p for p in connected if p not in platforms_with_digest]
for platform in platforms_without_digest:
    await _create_digest_for_platform(client, user_id, platform, assessment)

# Gap-filling: AFTER
for platform in connected_platforms:
    type_info = get_platform_project_type(platform)
    if type_info:
        type_key, _ = type_info
        result = await scaffold_project(client, user_id, type_key)
        # Uniqueness check inside scaffold_project handles idempotency

# Lifecycle expansion: BEFORE
await create_agent_record(title="Weekly Cross-Platform Insights", role="synthesize", ...)

# Lifecycle expansion: AFTER
await scaffold_project(client, user_id, "cross_platform_synthesis")
```

**Deleted code**: `PLATFORM_DIGEST_TITLES` dict in `composer.py`, `_create_digest_for_platform()` function, `BOOTSTRAP_TEMPLATES` dict in `onboarding_bootstrap.py`.

### 8. PROJECT.md Type Field

PROJECT.md gains a `type_key` field in its identity section:

```markdown
# Slack Recap

**Type**: slack_digest
**Status**: active

## Objective
- **Deliverable**: Daily Slack recap
- **Audience**: You
- **Format**: email
- **Purpose**: Stay informed on team activity without reading every message

## Contributors
- **slack-recap**: Daily platform digest
```

The `type_key` field is set at creation time and is immutable (changing a project's type is semantically a new project). It serves as:
- Uniqueness anchor for platform types
- Dashboard grouping key
- Registry lookup for type metadata (display_name, category)

### 9. Dashboard Implications

With all agents living inside projects, the dashboard becomes project-first:

- **Primary**: Project cards grouped by category (platform digests, synthesis, custom)
- **Each card**: Latest output date, next run, delivery status, attention items
- **No standalone agent grid** — agents visible within project detail
- **Platform projects** show platform icon + "Slack Recap" / "Gmail Digest" naturally

### 10. Versioning and Maintenance

Following established patterns (`PLATFORM_REGISTRY`, `ROLE_PORTFOLIOS`, `ROLE_PROMPTS`):

- Each registry entry has a `version` field (date string)
- Registry file has a version comment at the top referencing `api/prompts/CHANGELOG.md`
- Changes to registry entries logged in CHANGELOG.md under `[YYYY.MM.DD.N]`
- Registry is frozen at import time (dict, not mutable at runtime)

## Consequences

### Positive
- **Single creation path**: All projects flow through `scaffold_project()` — bootstrap, Composer, TP, and API routes
- **Deterministic scaffolding**: No LLM needed for platform projects; registry defines everything
- **Clean mental model**: Every agent belongs to a project; project is the universal container
- **Uniqueness enforcement**: Platform types are 1:1 with platform, checked at scaffold time (not title heuristics)
- **Extensible**: New project types added to registry dict, no code changes needed in consumers
- **PM stress-tested**: Single-agent projects skip PM (no overhead); multi-agent projects get PM (coordination)

### Negative
- **Migration**: Existing standalone agents need to be wrapped in projects (one-time migration)
- **Slight overhead for simple agents**: A single digest agent now lives under `/projects/{slug}/` — one extra folder level. Negligible.

### Deleted
- `BOOTSTRAP_TEMPLATES` dict in `onboarding_bootstrap.py`
- `PLATFORM_DIGEST_TITLES` dict in `composer.py`
- `_create_digest_for_platform()` function in `composer.py`
- `maybe_bootstrap_agent()` function — replaced by `maybe_bootstrap_project()`
- Standalone agent concept as default path (standalone remains possible via `custom` type but is not the bootstrap/Composer default)

## Resolved Decisions

### RD-1: Registry location — code-side dict
Follows `PLATFORM_REGISTRY`, `ROLE_PORTFOLIOS`, `BOOTSTRAP_TEMPLATES` pattern. Curated, deploy-time, ~10-15 entries. DB table adds unnecessary overhead.

### RD-2: Platform uniqueness — type_key in PROJECT.md
Stored in PROJECT.md at creation time. Checked by `scaffold_project()` before creation. Replaces title-matching heuristics in bootstrap idempotency.

### RD-3: PM gating — per-type `pm` field
`pm: False` for single-agent platform projects. `pm: True` for multi-agent projects. PM creation is a scaffolding decision, not a runtime decision.

### RD-4: Agent sources — `sources_from` field
`"platform"` = auto-populated from `platform_connections.landscape.selected_sources`. `"all_platforms"` = all connected platform sources. `None` = user/Composer specifies.

### RD-5: Assembly for single-agent projects — passthrough
When `assembly_spec: None` and `pm: False`, the agent's output IS the project deliverable. No assembly step. Delivery reads directly from the agent's output folder, which is also written to the project's contributions folder.

## Implementation Phases

### Phase 1: Registry + Scaffold Function (~200 lines) ✅ IMPLEMENTED
- Created `api/services/project_registry.py` with registry dict + access functions
- Created `scaffold_project()` in same file
- Added `type_key` field to `ProjectWorkspace.write_project()` and `read_project()`

### Phase 2: Bootstrap Migration (~100 lines net deletion) ✅ IMPLEMENTED
- Rewrote `onboarding_bootstrap.py` to call `scaffold_project()`
- Deleted `BOOTSTRAP_TEMPLATES` dict
- Deleted `maybe_bootstrap_agent()`, replaced with `maybe_bootstrap_project()`
- Updated `platform_worker.py` caller

### Phase 3: Composer Migration (~80 lines net deletion) ✅ IMPLEMENTED
- Deleted `PLATFORM_DIGEST_TITLES`, `_create_digest_for_platform()` from `composer.py`
- Rewrote gap-filling to use `get_platform_project_type()` + `scaffold_project()`
- Rewrote lifecycle expansion to use `scaffold_project("cross_platform_synthesis")`
- Rewrote cross-agent pattern handler to use `scaffold_project()`
- Updated coverage detection: `platforms_with_digest` → `platforms_with_coverage`
- Updated `_execute_create_project()` to pass `type_key="custom"` for LLM-driven projects
- Updated Composer prompt version in CHANGELOG.md

### Phase 4: Existing Agent Migration (migration SQL + one-time script)
- Migration: wrap existing standalone agents in projects
  - For each agent with `origin="system_bootstrap"` or Composer-created digest: create project wrapper
  - Set `type_key` based on agent role + sources
- Dashboard: switch to project-first view (separate ADR or inline with dashboard redesign)

### Phase 5: Dashboard Redesign (depends on P4b-3 plan)
- Project-first dashboard consuming `type_key` for grouping and display
- Platform project cards with platform icons
- Remove standalone agent grid

## Files

| Action | File | ~Lines |
|--------|------|--------|
| Create | `api/services/project_registry.py` | ~250 |
| Rewrite | `api/services/onboarding_bootstrap.py` | ~80 (down from ~230) |
| Modify | `api/services/composer.py` | -80 (delete digest gap-fill) |
| Modify | `api/services/workspace.py` | +10 (type_key in PROJECT.md) |
| Modify | `api/services/primitives/project.py` | +15 (type_key param) |
| Create | `supabase/migrations/115_wrap_standalone_agents.sql` | ~30 |
| Update | `api/prompts/CHANGELOG.md` | +15 |
| Update | `docs/adr/ADR-122-project-type-registry.md` | this file |
