'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 *
 * Routes to the appropriate surface component based on type.
 *
 * Key changes from ADR-023:
 * - Context browser deprecated (returns null, chat handles context)
 * - Idle surface still available but ChatFirstDesk is primary
 */

import { DeskSurface } from '@/types/desk';
import { DeliverableReviewSurface } from '@/components/surfaces/DeliverableReviewSurface';
import { DeliverableDetailSurface } from '@/components/surfaces/DeliverableDetailSurface';
import { DeliverableListSurface } from '@/components/surfaces/DeliverableListSurface';
import { WorkOutputSurface } from '@/components/surfaces/WorkOutputSurface';
import { WorkListSurface } from '@/components/surfaces/WorkListSurface';
import { ContextEditorSurface } from '@/components/surfaces/ContextEditorSurface';
import { DocumentViewerSurface } from '@/components/surfaces/DocumentViewerSurface';
import { DocumentListSurface } from '@/components/surfaces/DocumentListSurface';
import { PlatformListSurface } from '@/components/surfaces/PlatformListSurface';
import { PlatformDetailSurface } from '@/components/surfaces/PlatformDetailSurface';
import { DeliverableCreateSurface } from '@/components/surfaces/DeliverableCreateSurface';
import { IdleSurface } from '@/components/surfaces/IdleSurface';
import { HandoffBanner } from './HandoffBanner';

interface SurfaceRouterProps {
  surface: DeskSurface;
}

export function SurfaceRouter({ surface }: SurfaceRouterProps) {
  // Render the handoff banner above the surface content
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

    // ADR-037: Context browser deprecated - context is invisible (ADR-034)
    // Falls through to idle (chat home)
    case 'context-browser':
      // Show deprecation notice in dev, fall to idle
      if (process.env.NODE_ENV === 'development') {
        console.warn('ADR-037: context-browser surface is deprecated. Use chat for context.');
      }
      return <IdleSurface />;

    case 'context-editor':
      // Keep context editor for now - used when viewing specific memory
      return <ContextEditorSurface memoryId={surface.memoryId} />;

    case 'document-viewer':
      return <DocumentViewerSurface documentId={surface.documentId} />;

    case 'document-list':
      return <DocumentListSurface />;

    case 'platform-list':
      return <PlatformListSurface />;

    case 'platform-detail':
      return <PlatformDetailSurface platform={surface.platform} />;

    case 'deliverable-create':
      return <DeliverableCreateSurface initialPlatform={surface.initialPlatform} />;

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
