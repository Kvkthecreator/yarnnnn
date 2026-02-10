'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 *
 * Routes to the appropriate surface component based on type.
 *
 * ADR-037 Migration:
 * - Document surfaces migrated to /docs route
 * - Platform surfaces migrated to /integrations route
 * - Context browser deprecated (ADR-034)
 * - Remaining surfaces: deliverables, work, idle (TP-invoked)
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { DeskSurface } from '@/types/desk';
import { DeliverableReviewSurface } from '@/components/surfaces/DeliverableReviewSurface';
import { DeliverableDetailSurface } from '@/components/surfaces/DeliverableDetailSurface';
import { DeliverableListSurface } from '@/components/surfaces/DeliverableListSurface';
import { WorkOutputSurface } from '@/components/surfaces/WorkOutputSurface';
import { WorkListSurface } from '@/components/surfaces/WorkListSurface';
import { ContextEditorSurface } from '@/components/surfaces/ContextEditorSurface';
import { DeliverableCreateSurface } from '@/components/surfaces/DeliverableCreateSurface';
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
      case 'document-list':
        router.replace('/docs');
        break;
      case 'document-viewer':
        router.replace(`/docs/${surface.documentId}`);
        break;
      case 'platform-list':
        router.replace('/integrations');
        break;
      case 'platform-detail':
        router.replace(`/integrations/${surface.platform}`);
        break;
      case 'context-browser':
        // Context browser deprecated - stay on dashboard
        if (process.env.NODE_ENV === 'development') {
          console.warn('ADR-037: context-browser surface is deprecated. Use chat for context.');
        }
        break;
    }
  }, [surface, router]);

  // Render the surface content
  const renderSurface = () => {
    switch (surface.type) {
      case 'deliverable-review':
        return (
          <DeliverableReviewSurface
            deliverableId={surface.deliverableId}
            versionId={surface.versionId}
          />
        );

      case 'deliverable-detail':
        return <DeliverableDetailSurface deliverableId={surface.deliverableId} />;

      case 'deliverable-list':
        return <DeliverableListSurface status={surface.status} />;

      case 'work-output':
        return <WorkOutputSurface workId={surface.workId} outputId={surface.outputId} />;

      case 'work-list':
        return <WorkListSurface filter={surface.filter} />;

      case 'context-editor':
        // Keep context editor for now - used when viewing specific memory
        return <ContextEditorSurface memoryId={surface.memoryId} />;

      case 'deliverable-create':
        return <DeliverableCreateSurface initialPlatform={surface.initialPlatform} />;

      // Legacy surfaces redirect via useEffect above, show idle as fallback
      case 'document-list':
      case 'document-viewer':
      case 'platform-list':
      case 'platform-detail':
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
