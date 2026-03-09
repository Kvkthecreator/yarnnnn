# ADR-102: yarnnn as Internal Content Platform

**Date:** 2026-03-09
**Status:** Implementing
**Related:**
- [ADR-072: Unified Content Layer](ADR-072-unified-content-layer.md)
- [ADR-087: Deliverable Scoped Context](ADR-087-workspace-scoping-architecture.md)
- [ADR-092: Mode Taxonomy](ADR-092-deliverable-intelligence-mode-taxonomy.md)
- [ADR-101: Deliverable Intelligence Model](ADR-101-deliverable-intelligence-model.md)

---

## Problem

Deliverable outputs exist only in `deliverable_versions` — they are not part of the content layer that TP and other deliverables can search. This means:

1. A coordinator deliverable cannot reference the output of a recurring deliverable it orchestrates
2. TP cannot search across deliverable outputs alongside Slack/Gmail/Notion content
3. The accumulation loop (ADR-072) is incomplete — yarnnn's own generated knowledge doesn't feed back into the context pool

The `platform_content` unified content layer (ADR-072) already handles multi-platform content with retention, search, and TTL. Deliverable outputs are just another content platform.

---

## Decision

### yarnnn as a first-class platform

Add `"yarnnn"` to `PlatformType`. After successful deliverable delivery, write the version output as a `platform_content` row with `platform="yarnnn"`.

**Mapping:**

| platform_content field | Source |
|----------------------|--------|
| `platform` | `"yarnnn"` |
| `resource_id` | `deliverable_id` (the deliverable that produced it) |
| `resource_name` | Deliverable title |
| `item_id` | `version_id` |
| `content` | Version draft content |
| `content_type` | `deliverable_type` (e.g., `"newsletter"`, `"report"`) |
| `title` | `"{title} v{version_number}"` |
| `author` | `"yarnnn"` |
| `is_user_authored` | `False` |
| `metadata` | `{deliverable_type, mode, version_number, strategy}` |
| `source_timestamp` | Version `delivered_at` |
| `retained` | `True` (always — generated artifacts are not ephemeral) |
| `retained_reason` | `"yarnnn_output"` |
| `retained_ref` | `version_id` |

### What yarnnn content is NOT

- Not a sync target — no OAuth, no `platform_connections` row, no refresh primitive
- Not user-selectable as a "source" — it's automatic, tied to deliverable execution
- Not subject to TTL expiry — always retained (generated artifacts don't go stale the way synced messages do; they remain valuable as historical context)

### Where yarnnn content IS visible

- **Search primitive**: TP and headless agents can search `platform="yarnnn"` via the Search tool
- **System status**: Admin dashboard and system route show yarnnn content counts
- **Cross-deliverable context**: A deliverable's gathered context can include yarnnn platform_content from other deliverables

---

## Changes

| File | Change |
|------|--------|
| `api/services/platform_content.py` | Add `"yarnnn"` to `PlatformType`; add `"yarnnn_output"` to `RetainedReason`; add TTL entry |
| `api/services/deliverable_execution.py` | Write yarnnn_content row after successful delivery |
| `api/services/primitives/search.py` | Add `"yarnnn"` to Search platform enum |
| `api/routes/system.py` | Add `"yarnnn"` to `content_platforms` list |
| `api/routes/admin.py` | Add `"yarnnn"` to content-by-platform iteration; add `"yarnnn_output"` to retention reasons |
| `docs/adr/ADR-102-yarnnn-content-platform.md` | This document |

### Files NOT changed (intentionally)

| File | Why |
|------|-----|
| `api/services/primitives/refresh.py` | yarnnn content is written internally, not synced — refresh doesn't apply |
| `api/routes/integrations.py` | OAuth source selection — yarnnn has no OAuth connection |
| `api/routes/memory.py` | Writing style analysis per platform — not applicable to generated content |
| `api/routes/system.py:308` (`all_platforms`) | Drives platform sync status UI — yarnnn has no sync |

---

## Future Considerations

- **Retention pruning**: If yarnnn content grows large, consider version-based retention (keep last N versions per deliverable, expire older ones)
- **Embedding**: yarnnn content could be embedded for semantic search alongside other platform content
- **Cross-deliverable context in type prompt**: Coordinator deliverables could explicitly request yarnnn content from their orchestrated deliverables
