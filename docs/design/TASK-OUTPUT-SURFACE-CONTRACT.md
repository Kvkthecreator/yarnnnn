# Task Output Surface Contract

**Date:** 2026-04-09  
**Status:** Proposed  
**Related:**
- [AGENT-AND-TASK-SURFACE-PATTERNS.md](./AGENT-AND-TASK-SURFACE-PATTERNS.md) — shell rules for agent and task surfaces
- [SURFACE-ARCHITECTURE.md](./SURFACE-ARCHITECTURE.md) — canonical `/work` list/detail surface
- [../architecture/task-type-orchestration.md](../architecture/task-type-orchestration.md) — task registry and process model
- [../adr/ADR-130-html-native-output-substrate.md](../adr/ADR-130-html-native-output-substrate.md) — `output.md` + `output.html` substrate
- [../adr/ADR-166-registry-coherence-pass.md](../adr/ADR-166-registry-coherence-pass.md) — `output_kind` taxonomy
- [../adr/ADR-167-list-detail-surfaces.md](../adr/ADR-167-list-detail-surfaces.md) — kind-aware `/work` detail

## Purpose

Define the API contract that makes task runs **surface-ready** for `/work`.

The goal is singular:

- the backend emits one normalized task-run packet per output folder
- the frontend renders from that packet without parsing raw `manifest.json`
- `output_kind` continues to choose the shell, but the shell receives structured data instead of reconstructing meaning from markdown files and ad hoc manifest keys

## Problem

The current task output API is still file-oriented.

Today:

- `GET /api/tasks/{slug}/outputs/latest` returns `output.md`, optional `output.html`, a folder name, and raw `manifest`
- `GET /api/tasks/{slug}/outputs` returns folder/date/status plus raw `manifest`
- the four `/work` middle components still infer their meaning from a mix of:
  - task detail fields
  - markdown body content
  - raw manifest keys
  - output-folder conventions

That is not yet a surface contract. It is a storage wrapper.

Concrete issues in the current shape:

- `external_action` reads a raw `delivery_external_url` off manifest instead of a typed delivery block
- `accumulates_context` has no explicit domain-growth summary packet; the UI treats `output.md` as a changelog by convention
- `system_maintenance` has no typed notion of executor, touched paths, or deterministic posture
- `produces_deliverable` still gets the best experience only because `output.html` happens to be directly previewable
- history rows do not carry a coherent preview/status contract across kinds

## Decision

Use **one run-centric surface packet** as the canonical output API shape.

Do **not** introduce bespoke output endpoints per `output_kind`.

Do **not** keep the frontend dependent on raw manifest parsing as the long-term contract.

The storage substrate stays the same:

- `output.md`
- optional `output.html`
- `manifest.json`
- assets under the output folder

But the API contract moves up one layer:

- manifest stays a storage concern
- surface packet becomes the frontend concern

## Endpoint Strategy

Keep the existing output routes, but change what they return.

### End state

- `GET /api/tasks/{slug}/outputs/latest` → `TaskRunSurface`
- `GET /api/tasks/{slug}/outputs/{date_folder}` → `TaskRunSurface`
- `GET /api/tasks/{slug}/outputs` → `TaskRunSurfaceSummary[]`

This is the cleanest cut because the packet is about a **run**, not about a page.

It keeps the route model singular:

- task detail endpoint returns task identity
- output endpoints return run surfaces

No extra `/surface` endpoint is needed.

## Contract Shape

### 1. Full run packet

```ts
type TaskRunSurface = {
  run: {
    folder: string;
    created_at: string;
    status: "running" | "completed" | "delivered" | "failed" | "empty";
    output_kind: "accumulates_context" | "produces_deliverable" | "external_action" | "system_maintenance";
    type_key: string | null;
    mode: "recurring" | "goal" | "reactive" | null;
    version_number: number | null;
    layout_mode: string | null;
  };
  summary: {
    title: string;
    subtitle: string | null;
    text: string;
    timestamp_label: string | null;
  };
  artifact: {
    kind: "html_document" | "markdown_document" | "message" | "changelog" | "log" | "none";
    title: string | null;
    markdown: string | null;
    html: string | null;
    text: string | null;
  };
  delivery: {
    channel: string | null;
    status: "pending" | "delivered" | "failed" | null;
    delivered_at: string | null;
    external_id: string | null;
    external_url: string | null;
    error: string | null;
  } | null;
  exports: Array<{
    format: string;
    available: boolean;
  }>;
  provenance: {
    agent_slug: string | null;
    process_steps: number | null;
    context_reads: string[];
    context_writes: string[];
    sources: string[];
  };
  kind_data:
    | {
        output_kind: "accumulates_context";
        primary_domain: string | null;
        secondary_domains: string[];
        summary_markdown: string | null;
      }
    | {
        output_kind: "produces_deliverable";
        audience: string | null;
        deliverable_label: string | null;
      }
    | {
        output_kind: "external_action";
        target_platform: string | null;
        target_label: string | null;
        payload_markdown: string | null;
      }
    | {
        output_kind: "system_maintenance";
        executor: string | null;
        deterministic: true;
        log_markdown: string | null;
        touched_paths: string[];
      };
}
```

### 2. History/list summary packet

```ts
type TaskRunSurfaceSummary = {
  folder: string;
  created_at: string;
  status: "running" | "completed" | "delivered" | "failed" | "empty";
  output_kind: TaskRunSurface["run"]["output_kind"];
  artifact_kind: TaskRunSurface["artifact"]["kind"];
  text: string;
  external_url: string | null;
};
```

This summary is enough for:

- action history rows
- maintenance run history
- future run switchers in deliverable/report surfaces

## How The Four Kinds Map

### `accumulates_context`

The primary artifact is a **context-growth summary**, not a report.

Required packet behavior:

- `artifact.kind = "changelog"`
- `kind_data.primary_domain` and `kind_data.secondary_domains` are explicit
- `artifact.markdown` is the latest run summary
- `summary.text` explains what changed, not just that a file exists

The frontend should not infer these semantics from `context_writes[0]` plus a markdown body.

### `produces_deliverable`

The primary artifact is the deliverable itself.

Required packet behavior:

- `artifact.kind = "html_document"` when composed HTML exists
- fallback to `markdown_document` when only markdown exists
- `run.layout_mode` comes from the registry
- `exports` are surfaced directly from task type/export availability

This keeps deliverables artifact-led while still exposing provenance and delivery status in a consistent shape.

### `external_action`

The primary artifact is the **payload sent to another platform**, plus the delivery result.

Required packet behavior:

- `artifact.kind = "message"`
- `kind_data.target_platform` and `kind_data.target_label` are explicit
- `kind_data.payload_markdown` contains the user-visible message body when available
- `delivery.external_url` is first-class, not a raw manifest lookup

The frontend should never read `manifest.delivery_external_url` directly.

### `system_maintenance`

The primary artifact is a **deterministic log of upkeep**, not a user deliverable.

Required packet behavior:

- `artifact.kind = "log"`
- `kind_data.executor` identifies the deterministic executor
- `kind_data.deterministic = true`
- `kind_data.touched_paths` exposes what was changed or scanned when available

This makes maintenance tasks legible without pretending they behave like deliverable tasks.

## Serialization Rules

Backend serializer responsibility:

1. Read output folder files and manifest
2. Read task identity fields already known from `TASK.md`
3. Read registry metadata from `type_key`
4. Normalize into `TaskRunSurface`

The serializer should be the only place that knows:

- how `layout_mode` maps into artifact kind
- how delivery state is promoted from manifest
- how output markdown becomes `summary.text`
- how kind-specific blocks are assembled

Frontend responsibility:

- render the shell chosen by `output_kind`
- trust typed fields on the packet
- stop reading raw manifest keys directly

## What Stays Out Of The Contract

These remain storage/debug concerns, not normal UI contract fields:

- raw manifest JSON
- raw workspace file arrays beyond curated asset/export refs
- internal compose metadata
- backend-only execution details that are already covered by `GET /status` or `/steps`

If raw manifest inspection is ever needed for diagnostics, expose it through an explicit debug path or debug flag, not as a field normal UI code depends on.

## Migration Path

### Phase 1

Implement a backend serializer function:

```text
build_task_run_surface(task_row, task_md, task_type, output_folder) -> TaskRunSurface
```

Use it in:

- `GET /api/tasks/{slug}/outputs/latest`
- `GET /api/tasks/{slug}/outputs/{date_folder}`
- `GET /api/tasks/{slug}/outputs`

### Phase 2

Update frontend types and hooks:

- replace `TaskOutput` with `TaskRunSurface`
- replace raw history entries with `TaskRunSurfaceSummary`
- keep `useTaskOutputs()` but make it return typed surface packets

### Phase 3

Refactor the four `/work` middles to read only the new packet:

- `DeliverableMiddle` reads `artifact` + `exports`
- `TrackingMiddle` reads `kind_data.primary_domain` + `artifact.markdown`
- `ActionMiddle` reads `kind_data.target_*` + `delivery`
- `MaintenanceMiddle` reads `kind_data.executor` + `artifact.markdown`

### Phase 4

Delete raw-manifest reads from frontend code entirely.

That is the real completion point. Until then, the contract is not singular.

## Non-Goals

- replacing `output.md` / `output.html` storage
- changing ADR-166 `output_kind`
- merging task detail and output routes into one oversized payload
- creating one bespoke page or one bespoke endpoint per task type

## Why This Is The Right Next Step

The `/work` surface is now architecturally correct at the shell level.

The next bottleneck is the data contract.

Until task runs are serialized as surface-ready packets:

- the frontend will keep duplicating per-kind interpretation logic
- new task types will feel expensive to surface
- `output_kind` will be the page split, but not yet the API split

This contract makes the backend and frontend use the same unit of meaning:

- one task run
- one typed packet
- one shell chosen by `output_kind`

