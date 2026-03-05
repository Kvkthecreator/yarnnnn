import type { LandscapeResource } from '@/types';

export interface SyncMetrics {
  syncedResourceCount: number;
  errorCount: number;
  lastSyncedAt: string | null;
}

export function getSyncMetrics(
  resources: LandscapeResource[],
  selectedIds?: Set<string>
): SyncMetrics {
  const scopedResources = selectedIds
    ? resources.filter((resource) => selectedIds.has(resource.id))
    : resources;

  const syncedResourceCount = scopedResources.filter((resource) => !!resource.last_extracted_at).length;
  const errorCount = scopedResources.filter((resource) => !!resource.last_error).length;

  const lastSyncedAt = scopedResources.reduce((latest, resource) => {
    if (!resource.last_extracted_at) return latest;
    return !latest || resource.last_extracted_at > latest ? resource.last_extracted_at : latest;
  }, null as string | null);

  return {
    syncedResourceCount,
    errorCount,
    lastSyncedAt,
  };
}
