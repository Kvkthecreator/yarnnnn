'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 *
 * Routes to the appropriate surface component based on type.
 *
 * ADR-037 Migration Complete:
 * - Document surfaces → /docs route
 * - Platform surfaces → /integrations route
 * - Deliverable list/detail → /deliverables route
 * - Context browser → deprecated (ADR-034)
 *
 * Remaining surfaces (TP-invoked only):
 * - deliverable-review: Approve/reject generated content
 * - deliverable-create: Create new deliverable
 * - work-output, work-list: Work tracking
 * - context-editor: Edit specific memory
 * - idle: Default state
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { DeskSurface } from '@/types/desk';
import { DeliverableReviewSurface } from '@/components/surfaces/DeliverableReviewSurface';
import { DeliverableCreateSurface } from '@/components/surfaces/DeliverableCreateSurface';
import { WorkOutputSurface } from '@/components/surfaces/WorkOutputSurface';
import { WorkListSurface } from '@/components/surfaces/WorkListSurface';
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

      // Deliverable list/detail → /deliverables
      case 'deliverable-list':
        router.replace('/deliverables');
        break;
      case 'deliverable-detail':
        router.replace(`/deliverables/${surface.deliverableId}`);
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
      // TP-invoked surfaces (remain as surfaces)
      case 'deliverable-review':
        return (
          <DeliverableReviewSurface
            deliverableId={surface.deliverableId}
            versionId={surface.versionId}
          />
        );

      case 'deliverable-create':
        return <DeliverableCreateSurface initialPlatform={surface.initialPlatform} />;

      case 'work-output':
        return <WorkOutputSurface workId={surface.workId} outputId={surface.outputId} />;

      case 'work-list':
        return <WorkListSurface filter={surface.filter} />;

      case 'context-editor':
        return <ContextEditorSurface memoryId={surface.memoryId} />;

      // Legacy surfaces redirect via useEffect, show idle as fallback
      case 'document-list':
      case 'document-viewer':
      case 'platform-list':
      case 'platform-detail':
      case 'deliverable-list':
      case 'deliverable-detail':
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
