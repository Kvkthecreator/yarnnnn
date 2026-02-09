'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Routes to the appropriate surface component based on type
 */

import { DeskSurface } from '@/types/desk';
import { DeliverableReviewSurface } from '@/components/surfaces/DeliverableReviewSurface';
import { DeliverableDetailSurface } from '@/components/surfaces/DeliverableDetailSurface';
import { DeliverableListSurface } from '@/components/surfaces/DeliverableListSurface';
import { WorkOutputSurface } from '@/components/surfaces/WorkOutputSurface';
import { WorkListSurface } from '@/components/surfaces/WorkListSurface';
import { ContextBrowserSurface } from '@/components/surfaces/ContextBrowserSurface';
import { ContextEditorSurface } from '@/components/surfaces/ContextEditorSurface';
import { DocumentViewerSurface } from '@/components/surfaces/DocumentViewerSurface';
import { DocumentListSurface } from '@/components/surfaces/DocumentListSurface';
import { ProjectDetailSurface } from '@/components/surfaces/ProjectDetailSurface';
import { ProjectListSurface } from '@/components/surfaces/ProjectListSurface';
import { PlatformListSurface } from '@/components/surfaces/PlatformListSurface';
import { PlatformDetailSurface } from '@/components/surfaces/PlatformDetailSurface';
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

    case 'context-browser':
      return <ContextBrowserSurface scope={surface.scope} scopeId={surface.scopeId} />;

    case 'context-editor':
      return <ContextEditorSurface memoryId={surface.memoryId} />;

    case 'document-viewer':
      return <DocumentViewerSurface documentId={surface.documentId} />;

    case 'document-list':
      return <DocumentListSurface projectId={surface.projectId} />;

    case 'project-detail':
      return <ProjectDetailSurface projectId={surface.projectId} />;

    case 'project-list':
      return <ProjectListSurface />;

    case 'platform-list':
      return <PlatformListSurface />;

    case 'platform-detail':
      return <PlatformDetailSurface platform={surface.platform} />;

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
