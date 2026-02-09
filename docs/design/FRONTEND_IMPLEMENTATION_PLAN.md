# Frontend Implementation Plan: Platform-First Onboarding

> **Status**: Draft
> **Date**: 2026-02-09
> **Cross-reference**: [USER_FLOW_ONBOARDING_V2.md](./USER_FLOW_ONBOARDING_V2.md)

---

## Overview

This document maps the user flow stages from `USER_FLOW_ONBOARDING_V2.md` against existing frontend components, identifying gaps and implementation requirements.

---

## Component Inventory: What Exists

### Surfaces (Current)
| Surface | File | Status |
|---------|------|--------|
| `idle` | `IdleSurface.tsx` | ✅ Exists |
| `deliverable-detail` | `DeliverableDetailSurface.tsx` | ✅ Exists |
| `deliverable-review` | `DeliverableReviewSurface.tsx` | ✅ Exists |
| `deliverable-list` | `DeliverableListSurface.tsx` | ✅ Exists |
| `platform-list` | `PlatformListSurface.tsx` | ✅ Exists |
| `platform-detail` | `PlatformDetailSurface.tsx` | ✅ Exists |
| `context-browser` | `ContextBrowserSurface.tsx` | ✅ Exists |

### Onboarding Components
| Component | File | Status |
|-----------|------|--------|
| `PlatformOnboardingPrompt` | `PlatformOnboardingPrompt.tsx` | ✅ Exists |
| `PlatformSyncingBanner` | `PlatformOnboardingPrompt.tsx` | ✅ Exists |
| `PlatformConnectedBanner` | `PlatformOnboardingPrompt.tsx` | ✅ Exists |
| `NoPlatformsBanner` | `PlatformOnboardingPrompt.tsx` | ✅ Exists |

### Platform UI Components
| Component | File | Status |
|-----------|------|--------|
| `PlatformCard` | `ui/PlatformCard.tsx` | ✅ Exists |
| `PlatformCardGrid` | `ui/PlatformCardGrid.tsx` | ✅ Exists |
| `PlatformDetailPanel` | `ui/PlatformDetailPanel.tsx` | ✅ Exists |
| `PlatformIcons` | `ui/PlatformIcons.tsx` | ✅ Exists |

### Deliverable Creation Components
| Component | File | Status |
|-----------|------|--------|
| `DestinationSelector` | `ui/DestinationSelector.tsx` | ✅ Exists |
| `DeliverableSettingsModal` | `modals/DeliverableSettingsModal.tsx` | ✅ Exists |

### Hooks
| Hook | File | Status |
|------|------|--------|
| `usePlatformOnboardingState` | `hooks/usePlatformOnboardingState.ts` | ✅ Exists |
| `useOnboardingState` | `hooks/useOnboardingState.ts` | ✅ Exists (legacy) |

---

## Gap Analysis by User Flow Stage

### Stage 1: First Open (Cold Start) ✅ COMPLETE

**User Flow Requirement**: Show `PlatformOnboardingPrompt` for users with no platforms

**Current Implementation**:
- `IdleSurface.tsx` checks `usePlatformOnboardingState()`
- Returns `no_platforms` → renders `PlatformOnboardingPrompt`
- CTAs: "Connect Your First Platform" → `/settings`, "Skip" → dismisses banner

**Status**: ✅ Fully implemented

---

### Stage 2: Connect Platform(s) ⚠️ PARTIAL

**User Flow Requirement**: OAuth flow with sync progress feedback

**Current Implementation**:
- Settings page handles OAuth (external to desk surfaces)
- `usePlatformOnboardingState` tracks `platforms_syncing` state
- `PlatformSyncingBanner` shows when syncing

**Gaps**:
| Gap | Priority | Notes |
|-----|----------|-------|
| No in-app OAuth callback handling | Low | Redirects to `/settings` work |
| No granular sync progress | Medium | Only shows count, not per-resource |

**Recommended Actions**:
1. Consider adding `onViewProgress` callback to show detailed sync status
2. Backend already has `/integrations/jobs` - could surface this

---

### Stage 3: Dashboard (Platform Cards) ✅ COMPLETE

**User Flow Requirement**: Forest view with platform cards, click → detail panel

**Current Implementation**:
- `IdleSurface.tsx` renders `PlatformCardGrid` for connected platforms
- Click → opens `PlatformDetailPanel` (slide-in panel)
- Panel shows channels/resources, deliverables, recent context
- "Full View" → navigates to `platform-detail` surface

**Status**: ✅ Fully implemented (ADR-033 Phase 2)

---

### Stage 4: Create First Deliverable ⚠️ GAPS IDENTIFIED

**User Flow Requirement**: Destination-first wizard flow
1. Destination (where?)
2. Type (what?)
3. Sources (context?)
4. Schedule (when?)

**Current Implementation**:
- `DeliverableSettingsModal` exists but is for EDITING, not creating
- No dedicated creation wizard/flow component
- "New Deliverable" button → sends TP message: `"Help me create a new deliverable"`
- Relies on TP conversation to create deliverable (tool-based)

**Gaps**:
| Gap | Priority | Notes |
|-----|----------|-------|
| No UI wizard for deliverable creation | High | User flow shows 4-step wizard |
| Create relies on TP conversation | Medium | Works, but not guided |
| No source auto-suggestion | Medium | User flow mentions auto-suggest from destination |
| No type selector with descriptions | Low | Types are strings in settings modal |

**Recommended Actions**:

1. **Option A: TP-Guided Creation (Current)**
   - Keep current approach (TP creates via tools)
   - Enhance TP with clarify() tool to present wizard-like steps
   - Pros: Conversational, flexible
   - Cons: Less discoverable, requires typing

2. **Option B: Create Wizard Modal** (Recommended)
   - New `DeliverableCreateWizard` component
   - 4 steps matching user flow
   - Integrates `DestinationSelector` (already exists)
   - Calls `api.deliverables.create()` directly
   - Pros: Guided, clear, matches documentation
   - Cons: More code, parallel path to TP

3. **Option C: Hybrid**
   - Quick create: Click platform card → "Create deliverable here"
   - Pre-fills destination, shows simplified wizard
   - TP still available for complex cases

**Implementation Sketch for Option B**:
```typescript
// web/components/modals/DeliverableCreateWizard.tsx
interface DeliverableCreateWizardProps {
  open: boolean;
  onClose: () => void;
  onCreated: (deliverable: Deliverable) => void;
  initialDestination?: Destination; // Pre-fill from platform click
}

// Steps:
// 1. DestinationStep - uses existing DestinationSelector
// 2. TypeStep - new component with type cards
// 3. SourcesStep - simplified source picker (platform resources)
// 4. ScheduleStep - frequency/day/time pickers
```

---

### Stage 5: Domain Emerges ✅ BACKEND-DRIVEN

**User Flow Requirement**: Domains emerge from source patterns (invisible to user)

**Current Implementation**:
- ADR-034 defines domain inference logic
- Frontend consumes domains via `useActiveDomain` hook
- `context-browser` surface supports scope filtering

**Status**: ✅ Backend-driven, frontend consumes correctly

**Note**: Domain indicator in TP drawer was added in recent commit (ADR-034 Phase 4)

---

### Stage 6: Review and Trust Building ⚠️ PARTIAL

**User Flow Requirement**:
- Drafts appear in platform (Gmail drafts, Slack DM)
- Dashboard shows draft status with "Open in Gmail" link

**Current Implementation**:
- `DeliverableDetailSurface` shows latest output preview
- `DraftStatusIndicator` component exists
- Shows platform icon and status

**Gaps**:
| Gap | Priority | Notes |
|-----|----------|-------|
| No direct link to platform draft | Medium | Shows status but no "Open in Gmail" button |
| No Slack DM copy functionality | Medium | User flow shows "Copy Message" button |

**Recommended Actions**:
1. Add `openInPlatform` action to `DraftStatusIndicator`
2. For Gmail: Deep link to drafts folder
3. For Slack: Copy-to-clipboard with toast confirmation

---

### Stage 7: Scale - Multiple Domains ⚠️ PARTIAL

**User Flow Requirement**:
- Context browser shows domain tabs
- Dashboard evolves with cross-platform view

**Current Implementation**:
- `ContextBrowserSurface` supports scope filtering
- Domain selector would need to be added

**Gaps**:
| Gap | Priority | Notes |
|-----|----------|-------|
| No domain tab/selector in context browser | Medium | Only scope: user/deliverable |
| Dashboard doesn't show domain breakdown | Low | Platform cards are primary view |

**Recommended Actions**:
1. Add domain filter chips to context browser header
2. Consider domain-grouped view in future iteration

---

## Implementation Priority Matrix

### P0: Must Have (Blocking User Flow)
| Item | Effort | Owner |
|------|--------|-------|
| DeliverableCreateWizard (Option B or C) | Medium | - |

### P1: Should Have (Enhances Experience)
| Item | Effort | Owner |
|------|--------|-------|
| Platform draft deep links | Low | - |
| Slack copy-to-clipboard | Low | - |
| Granular sync progress | Medium | - |

### P2: Nice to Have (Polish)
| Item | Effort | Owner |
|------|--------|-------|
| Domain tabs in context browser | Medium | - |
| Source auto-suggestion in wizard | Medium | - |
| Deliverable type cards with descriptions | Low | - |

---

## Recommended Implementation Order

### Phase 1: Create Flow
1. Create `DeliverableCreateWizard` modal component
2. Wire up from "New Deliverable" button in `IdleSurface`
3. Add "Create deliverable" action to `PlatformDetailPanel`

### Phase 2: Draft Experience
4. Enhance `DraftStatusIndicator` with platform deep links
5. Add copy-to-clipboard for Slack drafts

### Phase 3: Domain Polish
6. Add domain filter to `ContextBrowserSurface`
7. Consider domain indicator in dashboard

---

## File Changes Required

### New Files
```
web/components/modals/DeliverableCreateWizard.tsx   # Main wizard
web/components/deliverables/TypeSelector.tsx        # Step 2 component
web/components/deliverables/SourcePicker.tsx        # Step 3 component
```

### Modified Files
```
web/components/surfaces/IdleSurface.tsx             # Add wizard trigger
web/components/ui/PlatformDetailPanel.tsx           # Add create action
web/components/ui/DraftStatusIndicator.tsx          # Add deep links
web/components/surfaces/ContextBrowserSurface.tsx   # Add domain filter
```

---

## API Requirements

Current APIs should support all needs:
- `POST /deliverables` - Create deliverable (exists)
- `GET /integrations/summary` - Platform summary (exists)
- `GET /integrations/{provider}/channels` - Slack channels (exists)
- `GET /context/domains` - List domains (may need to add)

---

## References

- [USER_FLOW_ONBOARDING_V2.md](./USER_FLOW_ONBOARDING_V2.md) - User flow document
- [ADR-032: Platform-Native Frontend](../adr/ADR-032-platform-native-frontend-architecture.md)
- [ADR-033: Platform-Centric UI](../adr/ADR-033-platform-centric-ui-architecture.md)
- [ADR-034: Emergent Context Domains](../adr/ADR-034-emergent-context-domains.md)
