# Deliverables Workspace Page — Overhaul

**Date:** 2026-03-05
**Status:** Implemented
**Related:**
- [ADR-092: Mode Taxonomy](../adr/ADR-092-deliverable-intelligence-mode-taxonomy.md)
- [ADR-093: Type Taxonomy](../adr/ADR-093-deliverable-types-overhaul.md)
- [List & Create Overhaul](DELIVERABLES-LIST-CREATE-OVERHAUL.md)
- [Workspace Layout](WORKSPACE-LAYOUT-NAVIGATION.md)

---

## Problem

The deliverables workspace page (`/deliverables/[id]`) was only lightly touched during the list+create overhaul. It still carried:

1. **Dead code** — `PLATFORM_ICON` (defined but never referenced), `formatSchedule()` (defined but never called), `formatDestination()` (defined but never called, list page has its own version)
2. **Platform-based identity** — identity chip used `getPlatformEmoji()` instead of mode icon, inconsistent with the mode-first list page
3. **Duplicated constants** — `TYPE_LABELS` defined in 3 files with slight variations
4. **Mode-unaware settings modal** — schedule section always shown (even for proactive/coordinator which use review cadence), no mode indicator
5. **Scattered header controls** — status text badge (hidden on mobile) + separate pause/resume icon button + settings gear = three elements doing two jobs

---

## Changes

### Dead code removal

| Item | Why dead |
|------|----------|
| `PLATFORM_ICON` record | Defined but never referenced (only emoji version was used) |
| `formatSchedule()` | Defined but never called in this file |
| `formatDestination()` | Defined but never called; list page has own more complete version |
| `getPlatformEmoji()` | Replaced by `DeliverableModeBadge` icon variant |
| Unused imports (`Mail`, etc.) | Only used by deleted helpers |

### Mode-first identity chip

Replaced `getPlatformEmoji(deliverable)` emoji with `<DeliverableModeBadge mode={deliverable.mode} variant="icon" />`. Now consistent with list page — mode (recurring/goal/reactive/proactive/coordinator) is the primary visual signal in the workspace header.

`PLATFORM_EMOJI` kept for `SourcePills` component — version source display is appropriately platform-specific.

### Shared type labels

Extracted `DELIVERABLE_TYPE_LABELS` to `web/lib/constants/deliverables.ts`. Consolidated 3 copies with slight variations into one shared constant. Standardized on fuller forms ("Status Update", "Deep Research") for new-user clarity.

### Mode-aware settings modal

- **Mode badge in header**: `DeliverableModeBadge` shown alongside type label so users see which mode they're configuring
- **Schedule gating**: Schedule section hidden for `proactive` and `coordinator` modes (they use review cadence, not fixed schedules)
- **Docstring fix**: Removed stale "Governance fixed to manual (draft mode)" reference

### Header controls consolidation

Merged separate status text badge and pause/resume icon button into a single clickable button-badge. Reduces two elements to one, always visible on all screen sizes, click target is obvious.

### Settings modal → drawer tab

`DeliverableSettingsModal` was absorbed into the workspace drawer as a tab (`DeliverableSettingsPanel`). Same form logic (destination, title, schedule, sources, archive), modal wrapper stripped. Settings gear button removed from header — settings is now the first drawer tab. See [Workspace Drawer Refactor](WORKSPACE-DRAWER-REFACTOR.md).

**Update (2026-03-09):** Recipient Context moved from Settings to the Instructions panel as the "Audience" section. Settings panel now covers: destination, title, schedule, data sources, archive.

---

## Files changed

| File | Change |
|------|--------|
| `web/app/(authenticated)/deliverables/[id]/page.tsx` | Dead code removal, mode-first identity, header controls consolidation, drawer refactor, inline version card |
| `web/lib/constants/deliverables.ts` | Created — shared `DELIVERABLE_TYPE_LABELS` |
| `web/app/(authenticated)/deliverables/page.tsx` | Import shared type labels |
| `web/components/modals/DeliverableSettingsModal.tsx` | **Deleted** — replaced by `DeliverableSettingsPanel` |
| `web/components/deliverables/DeliverableSettingsPanel.tsx` | Created — settings as drawer tab content |
| `web/components/surfaces/IdleSurface.tsx` | Import shared type labels |
