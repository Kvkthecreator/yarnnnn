# Deliverable Create Flow — TP Chat Handoff

**Date:** 2026-03-05
**Status:** Implemented
**Related:**
- [ADR-093: Deliverable Type Taxonomy](../adr/ADR-093-deliverable-types-overhaul.md)
- [ADR-092: Mode Taxonomy](../adr/ADR-092-deliverable-intelligence-mode-taxonomy.md)
- [Deliverable Create Flow Fix](DELIVERABLE-CREATE-FLOW-FIX.md)

---

## Problem

The deliverable create form had a two-step flow: type selection grid → config form (title, sources, destination, schedule). The config form was identical across all 7 types and missed type-specific fields (audience, subject, focus_area, signals, depth, etc.) that exist in backend Pydantic config classes.

TP already has `Write(ref="deliverable:new", ...)` with full type_config field support via flat field mappings and per-type skill prompts. The form duplicated what TP can do conversationally — and did it worse, since TP can ask follow-up questions, leverage context, and set all config fields.

---

## Decision

Keep the type selection grid (step 1) as a discovery UI. Replace step 2 with a redirect to TP chat, pre-seeded with type context.

### Flow

```
1. User clicks "New Deliverable" (any entry point)
2. Type selection grid at /deliverables/new
3. User clicks a type (e.g., Digest)
4. Redirect to /dashboard?create=digest
5. ChatFirstDesk pre-fills input: "I want to create a Digest deliverable"
6. User optionally adds context, presses Enter
7. TP skill detection matches type-specific skill
8. TP asks 1-2 key questions, then creates via Write primitive
```

### Pre-fill vs auto-send

Pre-fill + focus (not auto-send) because:
- User can add context before sending (e.g., "...for #engineering channel")
- Less jarring UX — one Enter press to send
- Input is editable — user stays in control

---

## What was deleted

| Item | File | Reason |
|------|------|--------|
| Step 2 config form (~400 lines) | `DeliverableCreateSurface.tsx` | Replaced by TP chat |
| `DELIVERY_OPTIONS`, `FREQUENCY_OPTIONS`, `DAY_OPTIONS` | `DeliverableCreateSurface.tsx` | Only used in step 2 |
| `DeliveryMode`, `DeliveryOption`, `PlatformResource` types | `DeliverableCreateSurface.tsx` | Only used in step 2 |
| All step-2 state + functions | `DeliverableCreateSurface.tsx` | Only used in step 2 |
| `initialPlatform` prop + handling | `DeliverableCreateSurface.tsx`, `desk.ts`, `SurfaceRouter.tsx` | No longer needed |

**Total removed:** ~635 lines (827 → 192)

---

## What was added

| Item | File | Purpose |
|------|------|---------|
| `?create={type}` URL param handling | `ChatFirstDesk.tsx` | Pre-fills chat input on type picker handoff |
| Coordinator skill | `skills.py` | Was missing — only 6 of 7 types had skills |
| `create a {type}` trigger patterns | `skills.py` | Pattern match for pre-filled handoff messages |
| Type-specific creation guidance table | `behaviors.py` | TP knows which 1-2 questions to ask per type |

---

## Files Changed

| File | Change |
|------|--------|
| `web/components/surfaces/DeliverableCreateSurface.tsx` | Stripped to type picker only (827 → 192 lines) |
| `web/components/desk/ChatFirstDesk.tsx` | Added `?create=` URL param handling |
| `api/services/skills.py` | Added coordinator skill + handoff trigger patterns |
| `api/agents/tp_prompts/behaviors.py` | Added type-specific creation guidance |
| `api/prompts/CHANGELOG.md` | Documented prompt changes (v2026.03.05.7) |
| `web/types/desk.ts` | Removed `initialPlatform` from `deliverable-create` surface |
| `web/components/desk/SurfaceRouter.tsx` | Simplified `deliverable-create` redirect |

---

## Entry Points (all work without modification)

1. **Deliverables list** "New" button → `/deliverables/new` (type picker) → type click → `/dashboard?create={type}`
2. **ChatFirstDesk** panel links → `/deliverables/new` (same flow)
3. **ChatFirstDesk** "Create a deliverable" button → `setInput('/create ')` (direct TP skill path)
4. **IdleSurface** "New Deliverable" → SurfaceRouter → `/deliverables/new`

---

## Patterns Reused

- `useSearchParams()` URL param reading: existing pattern in `DeskContext`, `DeliverableCreateSurface`, auth pages
- `router.replace()` URL cleanup: existing pattern in `SurfaceRouter`
- `DELIVERABLE_TYPE_LABELS` constant: `web/lib/constants/deliverables.ts`
- Skill trigger pattern matching: `api/services/skills.py` `detect_skill()`
