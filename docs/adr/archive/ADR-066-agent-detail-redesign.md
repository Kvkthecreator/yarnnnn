# ADR-066: Agent Detail Page Redesign — Delivery-First, No Governance

**Status**: Implemented
**Date**: 2026-02-19
**Relates to**: ADR-067 (Creation Simplification), ADR-042 (Execution), ADR-063 (Four-Layer Model)

### Implementation Status

**Backend** (`api/services/agent_execution.py`):
- ✅ Removed governance gate — always delivers immediately
- ✅ No more `staged` status — versions go to `delivered` or `failed`
- ✅ Added `update_version_for_delivery()` function
- ✅ Email-first delivery: `normalize_destination_for_delivery()` defaults to user's email
- ⚠️ Approval endpoints kept for backwards compatibility (deprecated)

**Backend** (`api/services/delivery.py` + `api/integrations/exporters/registry.py`):
- ✅ Added `email` platform alias → `gmail` exporter
- ✅ Platform lookup maps `email` → `gmail` for credentials

**Frontend** (`web/app/(authenticated)/agents/[id]/page.tsx`):
- ✅ Removed Approve/Reject buttons
- ✅ "Latest Output" → "Latest Delivery"
- ✅ "Previous Versions" → "Delivery History"
- ✅ Platform badge in header
- ✅ External link to delivered content
- ✅ Retry button for failed deliveries

**Frontend** (`web/components/modals/AgentSettingsModal.tsx`):
- ✅ Simplified destination to email-first (no complex DestinationSelector)
- ✅ Default destination is user's registered email

---

## Context

### Current Problems

The agent detail page has accumulated complexity around a **governance model** (approve/reject before delivery) that creates friction without value for single-user workflows:

1. **Governance mismatch**: User creates scheduled automation → system generates output → user must manually "approve" → only then delivery happens. This defeats the purpose of automation.

2. **Version status confusion**: `staged` / `reviewing` / `approved` / `rejected` — a workflow designed for multi-user collaboration that doesn't exist yet.

3. **Review as primary action**: The page centers on "Pending Review" with Approve/Reject buttons, but users want automated delivery, not a review queue.

4. **Pause/Resume vs Governance confusion**: Two independent controls (schedule vs approval) that don't relate well and create cognitive overhead.

### First Principles Assessment

**What is a agent?**
> A scheduled automation that generates content and delivers it to a destination.

**What does the user want?**
> Outputs delivered automatically on schedule. The ability to pause/resume, modify, or delete.

**What doesn't fit?**
> Self-approval before delivery. This is governance for future multi-user scenarios, not current single-user reality.

---

## Decision: Delivery-First, Remove Governance

### Core Principle

> A agent is a **scheduled automation**. When it runs, it delivers. User controls via schedule and pause/resume.

### What This Means

1. **No approval gate**: Generated content delivers immediately (or fails)
2. **Versions are delivery history**: Not pending items awaiting approval
3. **Pause/Resume is the only schedule control**: Stop/start automated runs
4. **Settings modify the automation**: Schedule, sources, destination

---

## New Mental Model

### Version Status (Simplified)

**Before:**
```typescript
type VersionStatus = "generating" | "staged" | "reviewing" | "approved" | "rejected" | "suggested";
```

**After:**
```typescript
type VersionStatus = "generating" | "delivered" | "failed";
```

| Status | Meaning |
|--------|---------|
| `generating` | Currently being created |
| `delivered` | Successfully sent to destination |
| `failed` | Generation or delivery failed |

### Controls (Simplified)

| Control | Function |
|---------|----------|
| **Pause/Resume** | Stop/start scheduled runs |
| **Settings** | Modify schedule, sources, destination |
| **Run Now** | Trigger immediate generation + delivery |
| **Archive** | Soft delete the agent |

**Removed:**
- Approve button
- Reject button
- Governance level selector

---

## New Page Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Back                                             ⏸ Pause   ⚙   │
│                                                                 │
│ 💬 Engineering Digest                                           │
│ Weekly on Monday at 09:00 → Slack #engineering                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─ Latest Delivery ───────────────────────────────────────────┐ │
│ │                                                             │ │
│ │  ✓ Delivered · Feb 19, 9:00 AM                              │ │
│ │  [View in Slack ↗]                                          │ │
│ │                                                             │ │
│ │  ▸ Show content                                             │ │
│ │                                                             │ │
│ │  Sources: #general (47 msgs) · #product (23 msgs)           │ │
│ │                                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─ Delivery History ──────────────────────────────────────────┐ │
│ │  ▸ Feb 12, 9:00 AM · ✓ Delivered                            │ │
│ │  ▸ Feb 5, 9:00 AM · ✓ Delivered                             │ │
│ │  ▸ Jan 29, 9:00 AM · ✗ Failed (Slack API error)             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─ Schedule ──────────────────────────────────────────────────┐ │
│ │  Next: Mon, Feb 24 at 9:00 AM (5 days)                      │ │
│ │                                              [Run Now]      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Changes from Previous ADR-066

| Before | After |
|--------|-------|
| "Latest Output" with Pending Review | "Latest Delivery" with delivery confirmation |
| Approve/Reject buttons | Removed entirely |
| "Previous Versions" | "Delivery History" (simpler mental model) |
| Editable content textarea | Read-only view with "Show content" expander |
| Feedback input for rejection | Removed |

### New Elements

1. **External link to delivered content**: "View in Slack ↗" / "View in Gmail ↗" when platform provides a permalink
2. **Delivery timestamp emphasis**: When it was delivered, not when it was generated
3. **Failed deliveries**: Show error reason with potential "Retry" option
4. **Platform badge in header**: Visual indicator of destination type

---

## Header Section

Emphasize platform identity with badge:

```
│ 💬 Engineering Digest                                           │
│ Weekly on Monday at 09:00 → Slack #engineering                  │
```

Platform badges:
- 💬 Slack agents
- 📧 Gmail/Email agents
- 📝 Notion agents
- 📊 Synthesis (cross-platform) agents

---

## Delivery History (Reconceptualized)

"Previous Versions" implied pending items. "Delivery History" is a log of what was sent.

Each entry shows:
- Delivery timestamp
- Status (Delivered / Failed)
- Expandable content preview
- Source attribution
- For failures: error message

---

## Backend Changes Required

### Execution Pipeline

Modify `execute_agent_generation()` to:
1. Generate content
2. Immediately attempt delivery (if destination configured)
3. Set version status to `delivered` or `failed`

**Remove:**
- `staged` status (versions don't wait for approval)
- Governance check before delivery
- Approval/rejection endpoints

### Database (Minimal)

- Keep `governance` field but ignore it (backwards compat)
- `staged_at` and `approved_at` become unused (don't migrate, just ignore)
- New: track `delivery_error` for failed deliveries (already exists)

---

## Settings Modal Simplification

Keep it focused on automation configuration:

### Keep
- **Schedule**: Frequency, day, time
- **Destination**: Platform + target
- **Sources**: Platform sources (channels, labels, pages)
- **Archive action**

### Remove
- Governance level selector (if it exists)
- Any approval-related settings

---

## Migration Path

### Phase 1: Backend — Auto-deliver
1. Update `execute_agent_generation()` to skip `staged`, go directly to delivery
2. New versions get `delivered` or `failed` status
3. Keep API backwards compatible (ignore governance param)

### Phase 2: Frontend — Detail page
1. Replace "Pending Review" UI with "Latest Delivery"
2. Remove Approve/Reject buttons
3. Rename "Previous Versions" to "Delivery History"
4. Add external link to delivered content
5. Add platform badge to header

### Phase 3: Cleanup
1. Remove approval endpoints from API
2. Remove governance from types (or mark deprecated)
3. Update create flow to not set governance

---

## What This Removes

| Removed | Reason |
|---------|--------|
| Approve/Reject workflow | Single-user doesn't need self-approval |
| `staged` / `reviewing` status | No longer needed without governance |
| Governance level setting | Not applicable to single-user |
| Editable content before approval | Can add "Edit & Resend" later if needed |
| Feedback notes on rejection | No rejection workflow |

---

## What This Enables

- **True automation**: Scheduled runs deliver without user action
- **Simpler mental model**: Agent = scheduled automation + history
- **Cleaner UI**: One status (delivered/failed), not approval queue
- **Future-ready**: Multi-user governance can be re-added as a feature flag

---

## Future Considerations

### Edit & Resend (Deferred)
User views delivered content, wants to send a correction:
- Creates new version
- User edits
- Delivers as correction

This is additive, not default governance.

### Multi-User Governance (Future)
When teams are supported:
- Manager configures "require approval" on certain agents
- Team member's scheduled run creates `pending_approval` version
- Manager approves → delivers

This would be opt-in per agent, not default behavior.

---

## Related

- [ADR-067](ADR-067-agent-creation-simplification.md) — Creation flow (aligns with this)
- [ADR-042](ADR-042-agent-execution-simplification.md) — Execution pipeline (needs update)
- [ADR-063](ADR-063-activity-log-four-layer-model.md) — Four-layer model (Work layer)
- [ADR-021](ADR-021-review-first-supervision-ux.md) — Superseded review-first model
