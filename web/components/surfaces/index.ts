/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-037: Chat-First Surface Architecture
 * ADR-066: Agent Detail Redesign
 * ADR-067: Agent Creation Simplification
 *
 * Surface component exports
 *
 * ADR-037 Migration Status:
 * - Documents: migrated to /docs, /docs/[id]
 * - Integrations: migrated to /integrations, /integrations/[provider]
 * - Agents: migrated to /agents, /agents/[id]
 * - Activity: DELETED (ADR-163) — absorbed into per-entity surfaces + Chat briefing
 * - Context browser: deprecated (use chat)
 *
 * ADR-066 Migration:
 * - AgentReviewSurface: DELETED — review happens inline on detail page
 *
 * ADR-067 Migration:
 * - AgentCreateSurface: DELETED — creation handled by TP chat (/dashboard?create)
 *
 * Remaining surfaces:
 * - ContextEditorSurface: Edit specific memory
 * - IdleSurface: Default chat state
 */

// Context/Memory surfaces (editor only - browser deprecated)
export { ContextEditorSurface } from './ContextEditorSurface';

// Idle state
export { IdleSurface } from './IdleSurface';
