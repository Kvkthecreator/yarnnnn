'use client';

/**
 * Notion Context Page
 *
 * Dedicated page for Notion integration management.
 * Two tabs: Sources (page selection) and Context (synced content feed).
 * Notion-specific: parent_type metadata, database badges.
 */

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FileCode, FileText, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { LandscapeResource } from '@/types';
import { usePlatformData } from '@/hooks/usePlatformData';
import { useSourceSelection } from '@/hooks/useSourceSelection';
import { PlatformNotConnected } from '@/components/context/PlatformNotConnected';
import { PlatformHeader } from '@/components/context/PlatformHeader';
import { CompactSyncStatus } from '@/components/context/CompactSyncStatus';
import { PlatformTabSwitcher } from '@/components/context/PlatformTabSwitcher';
import { PlatformContextFeed } from '@/components/context/PlatformContextFeed';
import { ResourceList } from '@/components/context/ResourceList';
import { ConnectionDetailsModal } from '@/components/context/ConnectionDetailsModal';

const BENEFITS = [
  'Sync pages and databases',
  'Surface Notion content to TP',
  'Write AI outputs back to pages',
];

function renderNotionMetadata(resource: LandscapeResource) {
  const parentType = resource.metadata?.parent_type as string | undefined;
  if (!parentType && resource.items_extracted === 0) return null;

  return (
    <div className="text-xs text-muted-foreground">
      {parentType && (
        <span>
          {parentType === 'workspace' && 'Top-level page'}
          {parentType === 'page' && 'Nested page'}
          {parentType === 'database' && 'Database item'}
        </span>
      )}
      {parentType && resource.items_extracted > 0 && <span> • </span>}
      {resource.items_extracted > 0 && (
        <span>
          {resource.items_extracted} items
          {resource.last_extracted_at && (
            <> synced {formatDistanceToNow(new Date(resource.last_extracted_at), { addSuffix: true })}</>
          )}
        </span>
      )}
    </div>
  );
}

export default function NotionContextPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [justConnected, setJustConnected] = useState(false);
  const [activeTab, setActiveTab] = useState<'sources' | 'context'>('sources');

  useEffect(() => {
    if (searchParams.get('status') === 'connected') {
      setJustConnected(true);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [searchParams]);

  const data = usePlatformData('notion');
  const sourceSelection = useSourceSelection({
    platform: 'notion',
    resources: data.resources,
    tierLimits: data.tierLimits,
    limitField: 'notion_pages',
    selectedIds: data.selectedIds,
    originalIds: data.originalIds,
    setSelectedIds: data.setSelectedIds,
    setOriginalIds: data.setOriginalIds,
    reload: data.reload,
  });

  if (data.loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!data.integration) {
    return (
      <PlatformNotConnected
        platform="notion"
        label="Notion"
        icon={<FileCode className="w-6 h-6" />}
        bgColor="bg-gray-50 dark:bg-gray-800/50"
        color="text-gray-700 dark:text-gray-300"
        benefits={BENEFITS}
      />
    );
  }

  return (
    <div className="h-full overflow-auto">
      <PlatformHeader
        label="Notion"
        icon={<FileCode className="w-5 h-5" />}
        bgColor="bg-gray-50 dark:bg-gray-800/50"
        color="text-gray-700 dark:text-gray-300"
        onConnectionDetails={() => setShowConnectionModal(true)}
      />

      <div className="p-4 md:p-6 space-y-6 max-w-6xl">
        {data.tierLimits && (
          <CompactSyncStatus
            platform="notion"
            tier={data.tierLimits.tier}
            syncFrequency={data.tierLimits.limits.sync_frequency}
            nextSync={data.tierLimits.next_sync}
            selectedCount={data.selectedIds.size}
            syncedCount={data.resources.filter(r => r.items_extracted > 0).length}
            errorCount={data.resources.filter(r => r.last_error).length}
            lastSyncedAt={data.resources.reduce((latest, r) => {
              if (!r.last_extracted_at) return latest;
              return !latest || r.last_extracted_at > latest ? r.last_extracted_at : latest;
            }, null as string | null)}
          />
        )}

        <PlatformTabSwitcher activeTab={activeTab} onTabChange={setActiveTab} />

        {activeTab === 'sources' && (
          <ResourceList
            resourceLabel="Pages"
            resourceLabelSingular="page"
            resourceIcon={<FileText className="w-4 h-4" />}
            workspaceName={data.integration.workspace_name}
            resources={data.resources}
            tierLimits={data.tierLimits}
            selectedIds={data.selectedIds}
            hasChanges={sourceSelection.hasChanges}
            atLimit={sourceSelection.atLimit}
            limit={sourceSelection.limit}
            saving={sourceSelection.saving}
            error={sourceSelection.error || data.error}
            showImportPrompt={sourceSelection.showImportPrompt}
            importing={sourceSelection.importing}
            importProgress={sourceSelection.importProgress}
            newlySelectedIds={sourceSelection.newlySelectedIds}
            onToggle={sourceSelection.handleToggle}
            onSave={sourceSelection.handleSave}
            onDiscard={sourceSelection.handleDiscard}
            onImport={sourceSelection.handleImport}
            onSkipImport={sourceSelection.handleSkipImport}
            renderMetadata={renderNotionMetadata}
            justConnected={justConnected}
            platformLabel="Notion"
          />
        )}

        {activeTab === 'context' && (
          <PlatformContextFeed platform="notion" />
        )}
      </div>

      <ConnectionDetailsModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        integration={data.integration}
        platformLabel="Notion"
        platformIcon={<FileCode className="w-5 h-5 text-gray-700 dark:text-gray-300" />}
        onDisconnect={() => router.push('/context')}
        tierInfo={data.tierLimits ? {
          tier: data.tierLimits.tier,
          sync_frequency: data.tierLimits.limits.sync_frequency,
          next_sync: data.tierLimits.next_sync,
        } : undefined}
      />
    </div>
  );
}
