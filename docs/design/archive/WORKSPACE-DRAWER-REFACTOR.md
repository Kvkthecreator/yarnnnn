# Workspace Drawer Refactor — Panel to Drawer + Inline Versions

**Date:** 2026-03-05
**Status:** Implemented
**Related:**
- [Workspace Layout & Navigation](WORKSPACE-LAYOUT-NAVIGATION.md) — updated layout diagrams
- [Deliverables Workspace Overhaul](DELIVERABLES-WORKSPACE-OVERHAUL.md) — settings modal absorption noted

---

## Problem

Both `/dashboard` and `/deliverables/[id]` used a shared `WorkspaceLayout` with a fixed 320px right panel (`hidden md:flex`). Three issues:

1. **Too narrow for content** — version preview markdown crammed into 320px is unreadable
2. **Invisible on mobile** — `hidden md:flex` meant no panel access below 768px
3. **Nested scroll contexts** — panel inside flex row created scroll-within-scroll
4. **Settings split** — configuration lived in a separate modal, disconnected from panel tabs

---

## Decision

### Drawer overlay replaces inline panel

CSS-based drawer (no library dependency):
- Fixed position, slides from right via `translateX` transition
- `w-full sm:w-[480px]` — full width on mobile, 480px on desktop
- Backdrop overlay + Escape key dismiss
- Trigger visible on ALL screen sizes (removed `hidden md:flex`)

### Version preview moves inline

Latest version shown as a collapsible card pinned above chat messages at full chat width. Collapsed by default: one-line summary with version number, status, timestamp, word count. Expands to full markdown preview. Schedule status + Run Now button inline. Older versions expandable below.

### Settings modal absorbed into drawer

`DeliverableSettingsModal` stripped of modal wrapper, moved to `DeliverableSettingsPanel`. Same form state and save logic. Now the first drawer tab. Header simplifies to `[Active/Paused toggle] [drawer trigger]`. Recipient Context moved from Settings to Instructions panel (2026-03-09).

---

## Data Domain to Surface Mapping

### INLINE (chat column)
- Latest version preview (full chat width for markdown)
- Older versions (collapsed list under preview)
- Schedule status + Run Now
- Chat messages + input

### DRAWER (slides from right, overlays)
**Deliverable page:** Settings | Versions | Memory | Instructions | Sessions
- **Settings**: Title, Schedule, Data Sources, Destination, Archive
- **Instructions**: Structured editor — Behavior (`deliverable_instructions`), Audience (`recipient_context`), Output Format (custom type only, `template_structure.format_notes`), Prompt Preview (read-only, what the agent sees)

**Dashboard:** Deliverables | Context

### HEADER
- Identity chip (mode icon + title + badge)
- Active/Paused toggle (deliverable only)
- Drawer trigger (single button, replaces both settings gear and panel toggle)

---

## Files changed

| File | Action |
|------|--------|
| `web/components/desk/WorkspaceLayout.tsx` | Rewritten — inline panel to drawer overlay |
| `web/app/(authenticated)/deliverables/[id]/page.tsx` | Inline version card, settings drawer tab, simplified header |
| `web/components/deliverables/DeliverableSettingsPanel.tsx` | Created — settings form as drawer tab content |
| `web/components/modals/DeliverableSettingsModal.tsx` | Deleted — replaced by DeliverableSettingsPanel |
| `web/components/tp/TPDrawer.tsx` | Deleted — deprecated, only used by deleted Desk.tsx |
| `web/components/desk/Desk.tsx` | Deleted — deprecated, replaced by ChatFirstDesk |
| `web/components/desk/ChatFirstDesk.tsx` | No changes — drawer refactor applied via WorkspaceLayout |
