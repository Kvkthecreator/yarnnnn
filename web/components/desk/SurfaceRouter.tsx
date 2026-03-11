'use client';

/**
 * ADR-037 + ADR-066 + ADR-067: Surface Architecture
 *
 * Routes to the appropriate surface component based on type.
 * Most surfaces now redirect to route-based pages.
 *
 * ADR-037 Migration Complete:
 * - Document surfaces → /docs route
 * - Platform surfaces → /integrations route
 * - Agent list/detail → /agents route
 * - Context browser → deprecated (ADR-034)
 *
 * ADR-066 Migration:
 * - agent-review → /agents/[id] (inline review)
 *
 * ADR-067 Migration:
 * - agent-create → DELETED (creation handled by TP chat — /dashboard?create)
 *
 * Remaining surfaces (TP-invoked only):
 * - context-editor: Edit specific memory
 * - idle: Default state
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { DeskSurface } from '@/types/desk';
import { ContextEditorSurface } from '@/components/surfaces/ContextEditorSurface';
import { IdleSurface } from '@/components/surfaces/IdleSurface';
import { HandoffBanner } from './HandoffBanner';

interface SurfaceRouterProps {
  surface: DeskSurface;
}

export function SurfaceRouter({ surface }: SurfaceRouterProps) {
  const router = useRouter();

  // Redirect legacy surfaces to their route equivalents
  useEffect(() => {
    switch (surface.type) {
      // Document surfaces → /docs
      case 'document-list':
        router.replace('/docs');
        break;
      case 'document-viewer':
        router.replace(`/docs/${surface.documentId}`);
        break;

      // Platform surfaces → /integrations
      case 'platform-list':
        router.replace('/integrations');
        break;
      case 'platform-detail':
        router.replace(`/integrations/${surface.platform}`);
        break;

      // Agent list/detail/review → /agents
      case 'agent-list':
        router.replace('/agents');
        break;
      case 'agent-detail':
        router.replace(`/agents/${surface.agentId}`);
        break;
      // ADR-066: Review now happens inline on detail page
      case 'agent-review':
        router.replace(`/agents/${surface.agentId}`);
        break;
      // Context browser deprecated
      case 'context-browser':
        if (process.env.NODE_ENV === 'development') {
          console.warn('ADR-037: context-browser surface is deprecated. Use chat for context.');
        }
        break;
    }
  }, [surface, router]);

  // Render the surface content
  const renderSurface = () => {
    switch (surface.type) {
      // ADR-066: agent-review redirects via useEffect, show idle as fallback
      case 'agent-review':
        return <IdleSurface />;

      case 'context-editor':
        return <ContextEditorSurface memoryId={surface.memoryId} />;

      // Legacy surfaces redirect via useEffect, show idle as fallback
      case 'document-list':
      case 'document-viewer':
      case 'platform-list':
      case 'platform-detail':
      case 'agent-list':
      case 'agent-detail':
      case 'context-browser':
      case 'idle':
      default:
        return <IdleSurface />;
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Handoff banner from TP - shown when navigating via tool */}
      <HandoffBanner />
      {/* Surface content */}
      <div className="flex-1 overflow-hidden">
        {renderSurface()}
      </div>
    </div>
  );
}
