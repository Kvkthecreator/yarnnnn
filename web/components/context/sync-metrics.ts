import type { LandscapeResource } from '@/types';

export interface SyncMetrics {
  syncedResourceCount: number;
  errorCount: number;
  lastSyncedAt: string | null;
}

export function getSyncMetrics(resources: LandscapeResource[]): SyncMetrics {
  const syncedResourceCount = resources.filter((resource) => !!resource.last_extracted_at).length;
  const errorCount = resources.filter((resource) => !!resource.last_error).length;

  const lastSyncedAt = resources.reduce((latest, resource) => {
    if (!resource.last_extracted_at) return latest;
    return !latest || resource.last_extracted_at > latest ? resource.last_extracted_at : latest;
  }, null as string | null);

  return {
    syncedResourceCount,
    errorCount,
    lastSyncedAt,
  };
}
