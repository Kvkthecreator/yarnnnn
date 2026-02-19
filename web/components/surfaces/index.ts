/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-037: Chat-First Surface Architecture
 * ADR-066: Deliverable Detail Redesign
 * ADR-067: Deliverable Creation Simplification
 *
 * Surface component exports
 *
 * ADR-037 Migration Status:
 * - Documents: migrated to /docs, /docs/[id]
 * - Integrations: migrated to /integrations, /integrations/[provider]
 * - Deliverables: migrated to /deliverables, /deliverables/[id], /deliverables/new
 * - Activity: migrated to /activity
 * - Context browser: deprecated (use chat)
 *
 * ADR-066 Migration:
 * - DeliverableReviewSurface: DELETED — review happens inline on detail page
 *
 * ADR-067 Migration:
 * - DeliverableCreateSurface: Now route-based at /deliverables/new
 *
 * Remaining surfaces (TP-invoked only):
 * - WorkOutputSurface: View work output details
 * - WorkListSurface: List work items
 * - ContextEditorSurface: Edit specific memory
 * - IdleSurface: Default chat state
 */

// Work surfaces (TP-invoked)
export { WorkOutputSurface } from './WorkOutputSurface';
export { WorkListSurface } from './WorkListSurface';

// Context/Memory surfaces (editor only - browser deprecated)
export { ContextEditorSurface } from './ContextEditorSurface';

// Idle state
export { IdleSurface } from './IdleSurface';
