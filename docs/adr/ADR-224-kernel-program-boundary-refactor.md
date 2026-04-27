# ADR-224: Kernel / Program Boundary — Template Residue Deletion

> **Status:** Proposed (spec only — code work follows after ratification)
> **Date:** 2026-04-27 (v2 same-day rewrite — first draft assumed registries were dispatch-authoritative; corrected after operator review pointed at ADR-188 + Axiom 1 corollary)
> **Authors:** KVK, Claude
> **Implements:** ADR-222 implementation roadmap, ADR 4
> **Related:** ADR-222 (OS framing), ADR-223 (Program Bundle Specification), ADR-188 (registries as templates), ADR-207 (TASK.md as dispatch authority), ADR-152 (Unified Directory Registry), ADR-187 (Trading), ADR-183 (Commerce), FOUNDATIONS Principle 10 (registries are template libraries) + Axiom 1 corollary (substrate grows from work)
> **Supersedes (in part):** none — refines ADR-188's commitment by enforcing it in code
> **Depended on by:** Compositor Layer ADR (forthcoming, ADR 2 — only weakly), Reference-Workspace Activation Flow ADR (forthcoming, ADR 5 — depends on bundle templates being canonical)

---

## Context

### The mistake the v1 draft caught (and v2 corrects)

The first draft of this ADR (v1, written same day) framed the problem as: *"kernel files like `task_types.py` contain trading-shaped declarations; the boundary refactor splits these into kernel-universal vs program-specific."* That framing assumed the registries are **dispatch-authoritative** — that runtime execution reads `TASK_TYPES["trading-signal"]` to know how to dispatch a task.

That assumption is wrong, and it had been wrong since **ADR-188 (registries as template libraries)** + **ADR-207 P4b (TASK.md as dispatch-authoritative)** + **FOUNDATIONS Axiom 1 corollary (substrate grows from work)**. Runtime execution reads `TASK.md` and `_domain.md` from the operator's workspace — it does not consult the kernel registries to know how to dispatch. The registries are already demoted to **referential template libraries**.

Operator review caught this: *"task types and workspace directories are guidance only. We actually demoted them as referential so workspaces are agnostic in nature and scaffolded real time based on inference. But directional guidance they're still probably a good way to consider the categorization."*

That correction changes the shape of ADR-224 substantially. The problem is real but smaller than the v1 draft sized it.

### What the registries actually do today

A grep audit (recorded here so the next review has a fact base):

**`task_types.TASK_TYPES`** — read at:
- **Task creation time** (`manage_task._handle_create`, `agent_creation.ensure_infrastructure_agent`) — convenience template expansion when an operator/YARNNN passes a `type_key` shortcut. The pipeline doesn't *require* the type_key to exist; it's a templating convenience.
- **Back-office scaffolding** (`workspace_init.py` scaffolds the 7 back-office tasks at signup using these templates).
- **Prompt-build fallback** (`compose/assembly.py`, `task_pipeline.py` line 2038 fallback) — used only when TASK.md doesn't declare `## Page Structure`.

**`directory_registry.WORKSPACE_DIRECTORIES`** — read at:
- **Domain scaffolding time** (`integrations.scaffold_context_domain`, `feedback_actuation` domain-path resolution).
- **Path utility helpers** (`get_domain`, `get_domain_folder`, `has_entity_tracker`, `get_tracker_path`, `get_synthesis_content`) — these read directory metadata that's already-known.
- **Working memory rendering** (`working_memory.py` line 473 surfaces directory list to YARNNN's compact index).

**`orchestration.CAPABILITIES`** — read at:
- **Exactly one place**: `task_derivation.py:123`, used to compute the derivation report when MANDATE.md is authored or a task is created (per ADR-207 P5). The dispatch path uses TASK.md `**Required Capabilities:**` directly, not this dict.

**`platform_tools.{SLACK,NOTION,GITHUB,COMMERCE,TRADING,EMAIL}_TOOLS`** — read at:
- **Tool surface assembly** at task execution time. This is the one place where program-specific code lives and is read at dispatch — but it's the *tool definitions* (Anthropic JSON schemas + Python handlers), which are kernel-shaped (not program-specific) per ADR-223 §1's analysis.

### What the boundary problem actually is

Given the audit, the boundary problem reframes:

1. **Kernel registries contain seed/template residue** for trading/portfolio/customers/revenue/etc. that belong to specific programs.
2. **Program bundles (post-ADR-223) already ship the canonical version** of those templates in MANIFEST.yaml + reference-workspace/.
3. **Both exist today** — kernel template + bundle template — which is the dual-canon Principle 7 violation, applied at the template layer (not the dispatch layer).

The fix is **template residue deletion**, not a dispatch refactor. The dispatch path was already program-agnostic.

---

## Decision

### 1. Boundary classification — what stays, what gets deleted from kernel

The new framing: kernel registries are **referential template libraries**. They should contain only **kernel-universal templates** — things every workspace plausibly uses regardless of which program is active.

#### `api/services/task_types.py`

**Stays in kernel** (21 entries, all kernel-universal):

- **Back-office (7)**: `back-office-agent-hygiene`, `back-office-workspace-cleanup`, `back-office-proposal-cleanup`, `back-office-outcome-reconciliation`, `back-office-reviewer-reflection`, `back-office-narrative-digest`, `back-office-reviewer-calibration`. Kernel infrastructure (per ADR-164).
- **Universal anchor (1)**: `daily-update`. Per ADR-161.
- **Generic knowledge-work (13)**: `track-competitors`, `track-market`, `track-relationships`, `track-projects`, `research-topics`, `competitive-brief`, `market-report`, `meeting-prep`, `stakeholder-update`, `project-status`, `content-brief`, `launch-material`, `maintain-overview`. Domain-shape-neutral templates available to any operator.

**Deletes from kernel** (3 entries):

- `revenue-report` — alpha-commerce-shaped. The bundle's MANIFEST.yaml is the source of truth.
- `trading-signal` — alpha-trader-shaped. Already declared in alpha-trader's MANIFEST.yaml per ADR-223 alignment.
- `portfolio-review` — alpha-trader-shaped. Already declared in alpha-trader's MANIFEST.yaml.

**Behavior change**: when YARNNN composes a `trading-signal` task, the bundle's MANIFEST is consulted (not the kernel registry). When an operator without alpha-trader-active asks for "trading-signal" by type_key, no such convenience template is found in kernel — YARNNN composes from first principles per ADR-188's intent, or asks the operator to clarify intent.

#### `api/services/directory_registry.py`

**Stays in kernel** (8 entries):

- **Universal substrate (2)**: `uploads`, `_shared`. Per Axiom 1 corollary — every workspace has these.
- **Generic knowledge-work domains (6)**: `competitors`, `market`, `relationships`, `projects`, `content_research`, `signals`. Domain-shape-neutral; any program operator might use these.
- **Capability-bundle-owned directories (3, kept in kernel)**: `slack`, `notion`, `github`. These are platform-bot-owned per ADR-158 (`temporal: true` flag). They're not program-specific — any program operator with Slack connected has `/workspace/context/slack/`. The directory naming convention belongs to the *capability*, not the *program*.

**Deletes from kernel** (4 entries):

- `customers`, `revenue` — alpha-commerce-shaped.
- `trading`, `portfolio` — alpha-trader-shaped (already declared in alpha-trader's MANIFEST.yaml).

**Behavior change**: at first-write to `/workspace/context/trading/`, the `_domain.md` is materialized from the bundle's MANIFEST `context_domains[].entities` declaration (or from operator-supplied frontmatter, whichever is present per ADR-188 Phase 2). The kernel registry no longer claims to know about trading.

#### `api/services/orchestration.py` `CAPABILITIES`

**Stays in kernel** (15 entries, all universal cognitive capabilities):

- Reasoning verbs: `summarize`, `detect_change`, `alert`, `cross_reference`, `data_analysis`, `investigate`, `produce_markdown`, `web_search`, `read_workspace`, `search_knowledge`
- Asset/render: `chart`, `mermaid`, `image`, `video_render`, `compose_html`

**Deletes from kernel** (9 entries):

- `read_slack`, `write_slack`, `read_notion`, `write_notion`, `read_github`, `read_commerce`, `write_commerce`, `read_trading`, `write_trading`.

**Behavior change**: `task_derivation.py` (the one caller) loads program bundles' MANIFEST `capabilities[]` declarations and unions them with kernel CAPABILITIES when computing the derivation report for a workspace. Workspace-specific resolution because the derivation report is itself workspace-scoped (it's written to `/workspace/memory/task_derivation.md` per ADR-207 P5).

#### `api/services/platform_tools.py`

**No code deletion here.** Per ADR-223 §1 analysis: tool definitions (Anthropic JSON schemas + Python handlers) stay in kernel as code; what moves to bundles is *which tools a program uses* (declared via `capabilities[].requires_connection` in MANIFEST). The wiring is already capability-gated per ADR-207 P3.

This is the architecturally honest classification: tool *availability per program* is bundle data; tool *implementation* is kernel code.

### 2. Loader — minimal, not a new service

The v1 draft proposed a new `api/services/program_registry.py` with `WorkspaceProgramView` union semantics and `workspace_id`-threaded callers. **v2 rejects this.** The actual call sites are few (~5 read sites for TASK_TYPES, ~6 for WORKSPACE_DIRECTORIES, 1 for CAPABILITIES). A lightweight bundle-loader that returns merged-with-kernel views per workspace is sufficient.

Proposed module: `api/services/program_bundles.py` (~80 lines):

```python
# api/services/program_bundles.py
# Lightweight bundle loader. Caches parsed MANIFEST.yaml per slug.
# Active-program resolution per workspace based on platform_connections.

from pathlib import Path
import yaml
from functools import lru_cache

BUNDLE_ROOT = Path("docs/programs")

@lru_cache(maxsize=32)
def _load_manifest(slug: str) -> dict | None:
    """Cached read of docs/programs/{slug}/MANIFEST.yaml."""
    path = BUNDLE_ROOT / slug / "MANIFEST.yaml"
    if not path.exists():
        return None
    with path.open() as f:
        return yaml.safe_load(f)

def list_active_bundles() -> list[dict]:
    """All bundles with status='active'. Cheap — reads filesystem."""
    return [m for slug in _all_slugs()
            if (m := _load_manifest(slug)) and m.get("status") == "active"]

def active_bundles_for_workspace(workspace_id: str) -> list[dict]:
    """
    Bundles active for this specific workspace, gated on platform connections.
    Active = bundle.status='active' AND workspace has at least one of
    bundle.capabilities[*].requires_connection connected.
    """
    ...

# Convenience views for the small number of callers
def task_types_for_workspace(workspace_id: str) -> dict[str, dict]:
    """Kernel TASK_TYPES merged with active bundles' task_types."""
    ...

def directories_for_workspace(workspace_id: str) -> dict[str, dict]:
    """Kernel WORKSPACE_DIRECTORIES merged with active bundles' context_domains."""
    ...

def capabilities_for_workspace(workspace_id: str) -> dict[str, dict]:
    """Kernel CAPABILITIES merged with active bundles' capabilities."""
    ...
```

**Caller migration is bounded:**

| Caller | Change |
|---|---|
| `manage_task.py` `_handle_create` (4 sites: lines 904, 1066, 1110, 1124, 1222, 1312, 1360-1361) | `get_task_type(type_key)` → `program_bundles.task_types_for_workspace(ws_id).get(type_key)`. Falls through to None if not found in kernel + active bundles, which `_handle_create` already handles (operator passes inline declarations). |
| `agent_creation.py:364` lazy specialist create | Reads TASK_TYPES for first-task scaffolding; updates to read merged view. |
| `workspace_init.py:364` back-office scaffolding | Reads kernel-only (back-office tasks are kernel-universal); no change needed. |
| `compose/assembly.py:60,154` page_structure fallback | Updates to read merged view. |
| `chat.py:966-968` task type lookup in YARNNN tool handler | Updates to read merged view (workspace_id available from session context). |
| `delivery.py:729` `delivery_requires_approval` | Reads kernel-only (ADR-178 declared this is task-type-keyed; kernel keeps the universal task types and their delivery_requires_approval flags). No change needed. |
| `working_memory.py:473` directory listing | Updates to read merged view for directory listing displayed to YARNNN. |
| `task_pipeline.py` directory helpers (~5 sites) | Updates to read merged view; helpers like `get_domain` become `get_domain(ws_id, name)`. |
| `feedback_actuation.py:248,317` domain_path resolution | Updates to read merged view. |
| `integrations.py:2137,2441` scaffold_context_domain | Updates to read merged view; if a workspace has alpaca connected and the alpha-trader bundle declares trading/portfolio domains, those scaffold cleanly. |
| `task_derivation.py:123` CAPABILITIES read | Updates to read merged view. |

Total: ~15 call sites get updated. No `workspace_id` threading where the call already has workspace context (most do); a couple of utility helpers gain `workspace_id` as a parameter.

### 3. Active-program resolution rule — same as v1

A program is active for a workspace when:
1. `MANIFEST.yaml`'s `status` is `active` (not `reference` / `deferred` / `archived`), AND
2. The workspace has at least one of the bundle's `capabilities[*].requires_connection` connected.

Capability-implicit, multi-program friendly, reversible. Same rationale as v1 §3 — that part of v1 was correct.

### 4. alpha-commerce bundle — same as v1

Currently homeless commerce-shaped artifacts (commerce_bot, customers/revenue domains, revenue-report task) get a `docs/programs/alpha-commerce/` bundle with `status: deferred` to capture the architectural fact. Bundle is mostly empty per ADR-223 §5 reference-workspace discipline. Real population happens when alpha-commerce activates as a primary program.

### 5. Migration path — atomic

Singular implementation discipline (CLAUDE.md rule 1): kernel registries lose their program-specific entries in the same commit as the bundle becomes the source of truth.

**Step 1 — Loader + alpha-commerce bundle creation**
- New `api/services/program_bundles.py` (~80 lines).
- New `docs/programs/alpha-commerce/` bundle (status: deferred, minimal MANIFEST/SURFACES/reference-workspace).
- Unit tests for `active_bundles_for_workspace()` and the merged-view helpers.

**Step 2 — Caller migration + kernel deletion (atomic with Step 1 in same PR)**
- Update ~15 callers to use merged views.
- Delete from kernel: 3 TASK_TYPES entries, 4 WORKSPACE_DIRECTORIES entries, 9 CAPABILITIES entries.
- Update `working_memory.py` directory listing to render merged view (so YARNNN sees trading/ when alpha-trader is active for the workspace, sees only the kernel-universal directories otherwise).
- Add test gate: `test_kernel_registries_have_no_program_residue`.

**Step 3 — Documentation sync**
- ADR-152, ADR-188 status notes (amended/validated by ADR-224).
- ADR-223 status (now backed by enforced boundary).
- `docs/architecture/SERVICE-MODEL.md` Frame 5 notes the boundary is enforced via bundle loader.
- `docs/architecture/os-framing-implementation-roadmap.md` ADR 4 → Implemented.
- CLAUDE.md ADR-registry entry for ADR-224 with implementation status.

Steps 1-3 land in one PR.

### 6. Test coverage

```python
# api/test_adr224_kernel_boundary.py

def test_kernel_task_types_have_no_program_residue():
    from services.task_types import TASK_TYPES
    program_keys = {"trading-signal", "portfolio-review", "revenue-report"}
    leaked = program_keys & set(TASK_TYPES.keys())
    assert not leaked, f"Program-specific TASK_TYPES still in kernel: {leaked}"

def test_kernel_directories_have_no_program_residue():
    from services.directory_registry import WORKSPACE_DIRECTORIES
    program_keys = {"trading", "portfolio", "customers", "revenue"}
    leaked = program_keys & set(WORKSPACE_DIRECTORIES.keys())
    assert not leaked, f"Program-specific directories still in kernel: {leaked}"

def test_kernel_capabilities_have_no_program_residue():
    from services.orchestration import CAPABILITIES
    program_keys = {"read_slack", "write_slack", "read_notion", "write_notion",
                    "read_github", "read_commerce", "write_commerce",
                    "read_trading", "write_trading"}
    leaked = program_keys & set(CAPABILITIES.keys())
    assert not leaked, f"Program-specific capabilities still in kernel: {leaked}"

def test_alpha_trader_active_bundle_supplies_trading_task_types():
    """When a workspace has alpaca connected, trading-signal becomes available
       via the merged view sourced from alpha-trader's MANIFEST.yaml."""
    ...

def test_alpha_trader_inactive_workspace_has_no_trading_task_types():
    """When a workspace has no alpaca connection, trading-signal is not in
       the merged task_types view — the bundle is not active for this workspace."""
    ...
```

### 7. What this ADR does NOT specify

Deferred:

- **Compositor implementation.** ADR forthcoming (ADR 2). The boundary refactor exposes bundle declarations cleanly; the compositor consumes them.
- **Activation flow UI.** ADR forthcoming (ADR 5).
- **alpha-commerce bundle full content.** Bundle is created with `status: deferred`; full population happens when the program activates.
- **Cross-program declaration conflicts.** Two bundles declaring the same task_type slug. Defer until alpha-commerce activates.

---

## What changed from v1 to v2 (record for future review)

| v1 framing | v2 framing | Why corrected |
|---|---|---|
| "Boundary refactor splits dispatch-authoritative registries" | "Template residue deletion — registries are already template libraries per ADR-188" | Operator pointed at FOUNDATIONS Principle 10 + Axiom 1 corollary; grep audit confirmed registries are not dispatch-authoritative |
| New `program_registry.py` service with `WorkspaceProgramView` and union semantics | Lightweight `program_bundles.py` (~80 lines) with merged-view helpers | The simpler shape suffices; the heavier service was over-engineered |
| ~50 call sites with `workspace_id` threading | ~15 call sites; most already have workspace context | Grep audit showed actual scope is much smaller |
| Atomic refactor as risk-mitigation | Atomic refactor as Principle 7 enforcement | Same conclusion, sharper rationale |
| "ADR 4 unblocks ADR 2" | "ADR 4 weakly aids ADR 2; both can land independently" | Compositor reads bundle declarations directly — doesn't strictly require kernel-side cleanup |

The lesson: when an ADR's central claim is "X violates Principle Y," verify the violation against the canon before scoping the fix. v1 was an honest mistake but a meaningful one — it would have produced a heavier refactor for a smaller actual problem.

---

## Consequences

### Positive

- **Principle 7 + Principle 10 enforced in code, not just docs.** Test gate fails if program-specific entries leak back into kernel registries. Bundles are the sole source for program-shaped templates.
- **Adding a program is purely additive (small commit).** alpha-prediction activation = create bundle + populate MANIFEST.yaml. No kernel touch. No new caller migration.
- **alpha-commerce gets an architectural home.** Captures shipped-but-homeless artifacts.
- **Multi-program workspaces compose naturally.** Two programs active = two MANIFESTs union into the merged view.
- **Refactor is small.** ~80 lines of new code (loader), ~15 caller updates, ~16 dict-entry deletions across 4 files. Sized in hours, not days.

### Negative / costs

- **15 call sites get the merged-view treatment.** Mechanical but real.
- **`api/services/program_bundles.py` is new infrastructure.** Small but adds a module to maintain.
- **alpha-commerce bundle creation.** Net new bundle (deferred status, minimal contents).
- **Cache invalidation if bundles change at runtime.** `lru_cache` on the loader is fine for now (bundles are repo-tracked, change at deploy time, not runtime). Revisit when the activation flow ADR (ADR 5) needs runtime mutation of bundles.

### Risks

- **Test gate too strict / too loose.** Mitigation: explicit allowlist of substrate-key references in code (back-office tasks legitimately read trading/ as substrate keys when scanning a workspace's accumulated state). The test asserts on dict-key membership, not on string-presence.
- **Caller missing the merged view.** A caller that imports TASK_TYPES directly bypasses the loader and would see kernel-only. Mitigation: code review + the test gate would catch any caller that references a program-specific key still expecting kernel presence.
- **alpha-commerce-deferred-but-loadable semantics.** The bundle exists; loader returns it from `_load_manifest()`; but `active_bundles_for_workspace()` filters by status='active'. A workspace with lemon_squeezy connected won't see alpha-commerce activate until its status flips. Documented explicitly to avoid surprises.

---

## Open questions

Explicitly deferred — none gate ratification.

- **`lru_cache` invalidation on bundle file change.** Process-restart suffices for now; revisit when bundles mutate at runtime (probably ADR 5 territory).
- **`get_domain(ws_id, name)` signature change ergonomics.** Some helpers gain `ws_id`; some keep their current signature (the kernel-universal ones). Decided per-helper during implementation.
- **Migration of existing kvk workspace.** kvk's substrate has trading/portfolio populated; the registry deletion doesn't touch substrate; reads continue to work because the alpha-trader bundle is active (alpaca connected). Verified during Step 2.

---

## Decision

**Adopt the kernel/program boundary refactor as defined above.** Kernel registries are referential template libraries holding only kernel-universal templates. Program-specific templates live in `docs/programs/{slug}/MANIFEST.yaml`. A lightweight `api/services/program_bundles.py` loader provides merged views per workspace. Active-program resolution is capability-implicit. Migration is atomic across loader creation, caller updates, and kernel-registry deletions. Test gate enforces the boundary going forward.
