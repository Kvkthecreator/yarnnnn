/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-037: Chat-First Surface Architecture
 * ADR-066: Deliverable Detail Redesign
 *
 * Surface component exports
 *
 * ADR-037 Migration Status:
 * - Documents: migrated to /docs, /docs/[id]
 * - Integrations: migrated to /integrations, /integrations/[provider]
 * - Deliverables: migrated to /deliverables, /deliverables/[id]
 * - Activity: migrated to /activity
 * - Context browser: deprecated (use chat)
 *
 * ADR-066 Migration:
 * - DeliverableReviewSurface: DELETED — review happens inline on detail page
 *
 * Remaining surfaces (TP-invoked only):
 * - DeliverableCreateSurface: Create new deliverable (chat-invoked)
 * - WorkOutputSurface: View work output details
 * - WorkListSurface: List work items
 * - ContextEditorSurface: Edit specific memory
 * - IdleSurface: Default chat state
 */

// Create surface (TP-invoked for creation flow)
export { DeliverableCreateSurface } from './DeliverableCreateSurface';

// Work surfaces (TP-invoked)
export { WorkOutputSurface } from './WorkOutputSurface';
export { WorkListSurface } from './WorkListSurface';

// Context/Memory surfaces (editor only - browser deprecated)
export { ContextEditorSurface } from './ContextEditorSurface';

// Idle state
export { IdleSurface } from './IdleSurface';
