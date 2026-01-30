/**
 * ADR-013: Conversation + Surfaces
 * Type definitions for the surface/drawer system
 */

export type SurfaceType = 'output' | 'context' | 'schedule' | 'export';

export type ExpandLevel = 'peek' | 'half' | 'full';

export interface SurfaceData {
  // For output surface
  outputId?: string;
  ticketId?: string;

  // For context surface
  projectId?: string;
  memoryId?: string;

  // For schedule surface
  scheduleId?: string;

  // For export surface
  exportType?: 'pdf' | 'docx' | 'email';
  content?: unknown;
  title?: string;
}

export interface SurfaceState {
  isOpen: boolean;
  type: SurfaceType | null;
  data: SurfaceData | null;
  expandLevel: ExpandLevel;
}

export type SurfaceAction =
  | { type: 'OPEN_SURFACE'; payload: { surfaceType: SurfaceType; data?: SurfaceData; expandLevel?: ExpandLevel } }
  | { type: 'CLOSE_SURFACE' }
  | { type: 'SET_EXPAND'; payload: { expandLevel: ExpandLevel } }
  | { type: 'SET_DATA'; payload: { data: SurfaceData } };

// UI action from TP tool responses
export interface TPUIAction {
  type: 'OPEN_SURFACE' | 'CLOSE_SURFACE';
  surface?: SurfaceType;
  data?: SurfaceData;
}
