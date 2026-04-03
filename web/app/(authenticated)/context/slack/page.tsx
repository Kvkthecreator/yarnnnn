'use client';

/**
 * Slack Context Page
 *
 * Dedicated page for Slack integration management.
 * Two tabs: Sources (channel selection) and Context (synced content feed).
 */

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Hash, Loader2 } from 'lucide-react';
import { getPlatformIcon } from '@/components/ui/PlatformIcons';
import { formatDistanceToNow } from 'date-fns';
import type { LandscapeResource } from '@/types';
import { usePlatformData } from '@/hooks/usePlatformData';
import { useSourceSelection } from '@/hooks/useSourceSelection';
import { PlatformNotConnected } from '@/components/context/PlatformNotConnected';
import { PlatformHeader } from '@/components/context/PlatformHeader';
import { PlatformTabSwitcher } from '@/components/context/PlatformTabSwitcher';
import { PlatformContextFeed } from '@/components/context/PlatformContextFeed';
import { ResourceList } from '@/components/context/ResourceList';
import { ConnectionDetailsModal } from '@/components/context/ConnectionDetailsModal';

const BENEFITS = [
  'Sync channels as context sources',
  'Surface recent messages to TP',
  'Track freshness of selected channels',
];

function renderSlackMetadata(resource: LandscapeResource) {
  const memberCount =
    (resource.metadata?.member_count as number | undefined)
    ?? (resource.metadata?.num_members as number | undefined);
  if (memberCount === undefined && !resource.last_extracted_at && resource.items_extracted === 0) return null;

  return (
    <div className="text-xs text-muted-foreground">
      {memberCount !== undefined && <span>{memberCount.toLocaleString()} members</span>}
      {memberCount !== undefined && (resource.items_extracted > 0 || !!resource.last_extracted_at) && <span> • </span>}
      {(resource.items_extracted > 0 || !!resource.last_extracted_at) && (
        <span>
          {resource.items_extracted > 0 ? `${resource.items_extracted} items` : '0 new items'}
          {resource.last_extracted_at && (
            <> synced {formatDistanceToNow(new Date(resource.last_extracted_at), { addSuffix: true })}</>
          )}
        </span>
      )}
    </div>
  );
}

export default function SlackContextPage() {
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

  const data = usePlatformData('slack');
  const sourceSelection = useSourceSelection({
    platform: 'slack',
    resources: data.resources,
    tierLimits: data.tierLimits,
    limitField: 'slack_channels',
    selectedIds: data.selectedIds,
    originalIds: data.originalIds,
    setSelectedIds: data.setSelectedIds,
    setOriginalIds: data.setOriginalIds,
    reload: data.reload,
  });

  if (data.loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Loading Slack channels...</p>
      </div>
    );
  }

  if (!data.integration) {
    return (
      <PlatformNotConnected
        platform="slack"
        label="Slack"
        icon={getPlatformIcon('slack', 'w-6 h-6')}
        bgColor="bg-purple-50 dark:bg-purple-950/30"
        color="text-purple-500"
        benefits={BENEFITS}
      />
    );
  }

  return (
    <div className="h-full overflow-auto">
      <PlatformHeader
        label="Slack"
        icon={getPlatformIcon('slack', 'w-5 h-5')}
        bgColor="bg-purple-50 dark:bg-purple-950/30"
        color="text-purple-500"
        onConnectionDetails={() => setShowConnectionModal(true)}
      />

      <div className="p-4 md:p-6 space-y-4 max-w-6xl">
        <div className="space-y-2">
          <PlatformTabSwitcher activeTab={activeTab} onTabChange={setActiveTab} />
        </div>

        {activeTab === 'sources' && (
          <ResourceList
            resourceLabel="Channels"
            resourceLabelSingular="channel"
            resourceIcon={<Hash className="w-4 h-4" />}
            workspaceName={data.integration.workspace_name}
            resources={data.resources}
            tierLimits={data.tierLimits}
            selectedIds={data.selectedIds}
            hasChanges={sourceSelection.hasChanges}
            atLimit={sourceSelection.atLimit}
            limit={sourceSelection.limit}
            saving={sourceSelection.saving}
            error={sourceSelection.error || data.error}
            onToggle={sourceSelection.handleToggle}
            onSave={sourceSelection.handleSave}
            onDiscard={sourceSelection.handleDiscard}
            renderMetadata={renderSlackMetadata}
            justConnected={justConnected}
            platformLabel="Slack"
          />
        )}

        {activeTab === 'context' && (
          <PlatformContextFeed
            platform="slack"
            selectedResourceIds={Array.from(data.selectedIds)}
            sourceLabel="channels"
          />
        )}
      </div>

      <ConnectionDetailsModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        integration={data.integration}
        platformLabel="Slack"
        platformIcon={getPlatformIcon('slack', 'w-5 h-5')}
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
