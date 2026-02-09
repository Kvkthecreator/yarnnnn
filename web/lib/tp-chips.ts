/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-034: Context (emergent domains)
 *
 * TP Chip utilities - human-readable labels for TP state indicators
 */

import { DeskSurface } from '@/types/desk';

/**
 * Get human-readable label for a surface
 */
export function getSurfaceLabel(surface: DeskSurface): string {
  switch (surface.type) {
    case 'idle':
      return 'Dashboard';
    case 'deliverable-review':
      return 'Review';
    case 'deliverable-detail':
      return 'Deliverable';
    case 'deliverable-list':
      return 'Deliverables';
    case 'work-output':
      return 'Work Output';
    case 'work-list':
      return 'Work';
    case 'context-browser':
      return 'Context';
    case 'context-editor':
      return 'Edit Context';
    case 'document-viewer':
      return 'Document';
    case 'document-list':
      return 'Documents';
    case 'platform-list':
      return 'Platforms';
    case 'platform-detail':
      return 'Platform';
    default:
      return 'Dashboard';
  }
}

/**
 * Get icon name for a surface (for lucide-react)
 */
export function getSurfaceIcon(surface: DeskSurface): string {
  switch (surface.type) {
    case 'idle':
      return 'LayoutDashboard';
    case 'deliverable-review':
      return 'FileCheck';
    case 'deliverable-detail':
    case 'deliverable-list':
      return 'Calendar';
    case 'work-output':
    case 'work-list':
      return 'Briefcase';
    case 'context-browser':
    case 'context-editor':
      return 'Brain';
    case 'document-viewer':
    case 'document-list':
      return 'FileText';
    case 'platform-list':
    case 'platform-detail':
      return 'Plug';
    default:
      return 'LayoutDashboard';
  }
}

/**
 * Context scope - what context TP is working under
 * ADR-034: Context is the user's accumulated knowledge, auto-scoped by deliverable
 */
export type ContextScope =
  | { type: 'user'; label: 'Your context' }
  | { type: 'deliverable'; label: string; deliverableId: string };

/**
 * Get context scope from surface
 * Context is automatically scoped when viewing a deliverable
 */
export function getContextScope(surface: DeskSurface): ContextScope {
  switch (surface.type) {
    case 'deliverable-review':
    case 'deliverable-detail':
      return {
        type: 'deliverable',
        label: 'Deliverable context',
        deliverableId: surface.deliverableId,
      };
    case 'context-browser':
      if (surface.scope === 'deliverable' && surface.scopeId) {
        return {
          type: 'deliverable',
          label: 'Deliverable context',
          deliverableId: surface.scopeId,
        };
      }
      return { type: 'user', label: 'Your context' };
    default:
      return { type: 'user', label: 'Your context' };
  }
}

/**
 * TP state indicator data
 */
export interface TPStateIndicators {
  /** What surface TP is "seeing" */
  surface: {
    label: string;
    icon: string;
  };
  /** What context TP is working under */
  context: ContextScope;
  /** Deliverable focus (if any) */
  deliverable: {
    active: boolean;
    label: string;
    id?: string;
  };
}

/**
 * Get all TP state indicators from current surface
 */
export function getTPStateIndicators(surface: DeskSurface): TPStateIndicators {
  const surfaceLabel = getSurfaceLabel(surface);
  const surfaceIcon = getSurfaceIcon(surface);
  const context = getContextScope(surface);

  // Determine deliverable focus
  let deliverable: TPStateIndicators['deliverable'] = {
    active: false,
    label: 'No deliverable',
  };

  if (surface.type === 'deliverable-detail' || surface.type === 'deliverable-review') {
    deliverable = {
      active: true,
      label: 'Active',
      id: surface.deliverableId,
    };
  }

  return {
    surface: { label: surfaceLabel, icon: surfaceIcon },
    context,
    deliverable,
  };
}
