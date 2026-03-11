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
      return 'Agent';
    case 'agent-review':
      return 'Review';
    case 'agent-detail':
      return 'Agent';
    case 'agent-list':
      return 'Agents';
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
      return 'Agent';
  }
}

/**
 * Get icon name for a surface (for lucide-react)
 */
export function getSurfaceIcon(surface: DeskSurface): string {
  switch (surface.type) {
    case 'idle':
      return 'LayoutDashboard';
    case 'agent-review':
      return 'FileCheck';
    case 'agent-detail':
    case 'agent-list':
      return 'Calendar';
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
 * ADR-034: Context is the user's accumulated knowledge, auto-scoped by agent
 */
export type ContextScope =
  | { type: 'user'; label: 'Your context' }
  | { type: 'agent'; label: string; agentId: string };

/**
 * Get context scope from surface
 * Context is automatically scoped when viewing an agent
 */
export function getContextScope(surface: DeskSurface): ContextScope {
  switch (surface.type) {
    case 'agent-review':
    case 'agent-detail':
      return {
        type: 'agent',
        label: 'Agent context',
        agentId: surface.agentId,
      };
    case 'context-browser':
      if (surface.scope === 'agent' && surface.scopeId) {
        return {
          type: 'agent',
          label: 'Agent context',
          agentId: surface.scopeId,
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
  /** Agent focus (if any) */
  agent: {
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

  // Determine agent focus
  let agent: TPStateIndicators['agent'] = {
    active: false,
    label: 'No agent',
  };

  if (surface.type === 'agent-detail' || surface.type === 'agent-review') {
    agent = {
      active: true,
      label: 'Active',
      id: surface.agentId,
    };
  }

  return {
    surface: { label: surfaceLabel, icon: surfaceIcon },
    context,
    agent,
  };
}
