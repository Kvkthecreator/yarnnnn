/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-037: Chat-First Surface Architecture
 *
 * Surface component exports
 *
 * Note: Document and Platform surfaces migrated to route pages (ADR-037)
 * - Documents: /docs, /docs/[id]
 * - Integrations: /integrations, /integrations/[provider]
 * - Context browser: deprecated (use chat)
 */

// Core surfaces
export { DeliverableReviewSurface } from './DeliverableReviewSurface';
export { DeliverableDetailSurface } from './DeliverableDetailSurface';
export { DeliverableListSurface } from './DeliverableListSurface';
export { DeliverableCreateSurface } from './DeliverableCreateSurface';
export { IdleSurface } from './IdleSurface';

// Work surfaces
export { WorkOutputSurface } from './WorkOutputSurface';
export { WorkListSurface } from './WorkListSurface';

// Context/Memory surfaces (editor only - browser deprecated)
export { ContextEditorSurface } from './ContextEditorSurface';
