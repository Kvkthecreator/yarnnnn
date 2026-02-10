/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-037: Chat-First Surface Architecture
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
 * Remaining surfaces (TP-invoked only):
 * - DeliverableReviewSurface: Review/approve generated content
 * - DeliverableCreateSurface: Create new deliverable (chat-invoked)
 * - WorkOutputSurface: View work output details
 * - WorkListSurface: List work items
 * - ContextEditorSurface: Edit specific memory
 * - IdleSurface: Default chat state
 */

// Review surface (TP-invoked for approval flow)
export { DeliverableReviewSurface } from './DeliverableReviewSurface';

// Create surface (TP-invoked for creation flow)
export { DeliverableCreateSurface } from './DeliverableCreateSurface';

// Work surfaces (TP-invoked)
export { WorkOutputSurface } from './WorkOutputSurface';
export { WorkListSurface } from './WorkListSurface';

// Context/Memory surfaces (editor only - browser deprecated)
export { ContextEditorSurface } from './ContextEditorSurface';

// Idle state
export { IdleSurface } from './IdleSurface';
