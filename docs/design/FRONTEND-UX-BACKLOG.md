# Frontend UX Backlog

**Date:** 2026-04-01  
**Status:** Deferred — stabilize backend + test execution loop first

---

## P0: Fix before launch

### Nav breadcrumb
- Header nav shows "Workfloor" even on `/tasks/[slug]` pages
- Should show current location: task title, or "Tasks" section name
- Nav dropdown should be context-aware (highlight current section)

### Workfloor dashboard (default main panel)
- Replace isometric room with workspace dashboard when nothing selected
- Show: upcoming scheduled runs, recent completions, context domain health
- Data already available from tasks table + workspace_files

### Files tab layout polish
- Content viewer positioning between panels needs responsive handling
- Mobile/narrow viewport consideration

## P1: After launch

### Workfloor absorbs list pages
- `/tasks` list page → redundant (workfloor Tasks tab)
- `/agents` list page → redundant (workfloor Files tab under /agents/)
- `/context` page → redundant (workfloor Files tab)
- Redirect these routes to `/workfloor`

### Task detail inline (future)
- IDE-style tabs in main panel
- Click task from list → opens in tab instead of redirect
- Requires task detail refactored into standalone component

### Agent detail in Files tab
- Click agent folder → show agent detail view (not just files)
- Domain health, task assignments, reflections summary

### Context domain cards
- Visual summary cards per domain (entity count, freshness, health)
- Replace raw file listing for /workspace/context/ root
