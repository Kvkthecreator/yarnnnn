# Agent Create Flow — Type Config Validation Fix

**Date:** 2026-03-05
**Status:** Implemented
**Related:**
- [ADR-093: Agent Type Taxonomy](../adr/ADR-093-agent-types-overhaul.md)
- [Agents List & Create Overhaul](DELIVERABLES-LIST-CREATE-OVERHAUL.md)

---

## Problem

`validate_type_config()` in `api/routes/agents.py` mapped **20+ legacy type names** (e.g., `status_report`, `slack_channel_digest`, `research_brief`) to config classes that **no longer exist** (e.g., `StatusReportConfig`, `SlackChannelDigestConfig`). ADR-093 replaced all legacy types with 7 purpose-first types, but the validation function was never updated.

**Impact:** Every agent created with a new type (`digest`, `brief`, `status`, `watch`, `deep_research`, `coordinator`) silently fell through to `CustomConfig`, losing type-specific configuration fields. The `custom` type was the only one that worked correctly by coincidence.

Additionally, the stale map referenced ~15 undefined Python classes — any code path hitting a legacy type name would crash with `NameError`.

---

## Fix

Replaced the stale `config_classes` dict with the current 7 types mapped to their existing Pydantic config classes:

| Type | Config Class |
|------|-------------|
| `digest` | `DigestConfig` |
| `brief` | `BriefConfig` |
| `status` | `StatusConfig` |
| `watch` | `WatchConfig` |
| `deep_research` | `DeepResearchConfig` |
| `coordinator` | `CoordinatorConfig` |
| `custom` | `CustomConfig` |

The config classes themselves (lines 132-182) were already correct — only the validation mapping was stale.

---

## What was deleted

| Item | Reason |
|------|--------|
| 20+ legacy type mappings in `config_classes` dict | Types removed by ADR-093, config classes undefined |
| Legacy tier comments ("Tier 1 - Stable", "Beta Tier", etc.) | Replaced by single "stable" tier for all types |

---

## Frontend Audit (No Changes Needed)

The create surface (`web/components/surfaces/AgentCreateSurface.tsx`) sends:
- `title`, `agent_type`, `mode` (implicit from type), `schedule`, `type_classification`, `destination`, `sources`
- No `type_config` sent — backend correctly defaults via `get_default_config()`
- Schedule correctly sends `{ frequency: 'custom' }` for proactive/coordinator modes
- All 7 types have correct implicit mode mappings
- Source selection is hidden (no `primaryPlatform` set) — correct per ADR-093 design

No frontend changes required.

---

## File Changed

**`api/routes/agents.py`** — `validate_type_config()` function (lines 1536-1561)
