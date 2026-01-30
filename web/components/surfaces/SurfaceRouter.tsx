'use client';

/**
 * ADR-013: Conversation + Surfaces
 * Routes to the appropriate surface content based on type
 */

import { useSurface } from '@/contexts/SurfaceContext';
import { Drawer, SidePanel } from './Drawer';
import { OutputSurface } from './OutputSurface';
import { ContextSurface } from './ContextSurface';
import { ScheduleSurface } from './ScheduleSurface';
import { ExportSurface } from './ExportSurface';
import { useMediaQuery } from '@/hooks/useMediaQuery';

export function SurfaceRouter() {
  const { state } = useSurface();
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  const renderContent = () => {
    if (!state.type) return null;

    switch (state.type) {
      case 'output':
        return <OutputSurface data={state.data} />;
      case 'context':
        return <ContextSurface data={state.data} />;
      case 'schedule':
        return <ScheduleSurface data={state.data} />;
      case 'export':
        return <ExportSurface data={state.data} />;
      default:
        return null;
    }
  };

  // Use SidePanel on desktop, Drawer on mobile
  const Container = isDesktop ? SidePanel : Drawer;

  return (
    <Container>
      {renderContent()}
    </Container>
  );
}
