'use client';

/**
 * ADR-013: Conversation + Surfaces
 * Routes to the appropriate surface component.
 *
 * Now uses unified WorkspacePanel for Context, Work, and Outputs tabs.
 * Export surface still opens as a separate modal/drawer.
 */

import { useSurface } from '@/contexts/SurfaceContext';
import { WorkspacePanel } from './WorkspacePanel';
import { ExportSurface } from './ExportSurface';
import { Drawer, SidePanel } from './Drawer';
import { useMediaQuery } from '@/hooks/useMediaQuery';

export function SurfaceRouter() {
  const { state } = useSurface();
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  // Export gets its own modal/drawer (different UX)
  if (state.type === 'export' && state.isOpen) {
    const Container = isDesktop ? SidePanel : Drawer;
    return (
      <Container>
        <ExportSurface data={state.data} />
      </Container>
    );
  }

  // Everything else uses the unified WorkspacePanel
  return <WorkspacePanel />;
}
