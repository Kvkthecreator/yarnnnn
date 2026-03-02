'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { PlatformContentItem } from '@/types';

type PlatformKey = 'slack' | 'gmail' | 'notion' | 'calendar';

interface PlatformContextFeedProps {
  platform: PlatformKey;
}

export function PlatformContextFeed({ platform }: PlatformContextFeedProps) {
  const [items, setItems] = useState<PlatformContentItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [retainedCount, setRetainedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const loadItems = useCallback(async (offset = 0) => {
    if (offset === 0) setLoading(true);
    else setLoadingMore(true);

    try {
      const result = await api.integrations.getPlatformContext(platform, {
        limit: 30,
        offset,
      });
      if (offset === 0) {
        setItems(result.items || []);
      } else {
        setItems(prev => [...prev, ...(result.items || [])]);
      }
      setTotalCount(result.total_count);
      setRetainedCount(result.retained_count);
    } catch (err) {
      console.error('Failed to load platform context:', err);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [platform]);

  useEffect(() => {
    loadItems(0);
  }, [loadItems]);

  const grouped = useMemo(() => {
    const groups: Record<string, { name: string; items: PlatformContentItem[] }> = {};
    for (const item of items) {
      const key = item.resource_id;
      if (!groups[key]) {
        groups[key] = { name: item.resource_name || item.resource_id, items: [] };
      }
      groups[key].items.push(item);
    }
    // Sort groups by most recent item first
    return Object.entries(groups).sort(([, a], [, b]) => {
      const aTime = a.items[0]?.source_timestamp || a.items[0]?.fetched_at || '';
      const bTime = b.items[0]?.source_timestamp || b.items[0]?.fetched_at || '';
      return bTime.localeCompare(aTime);
    });
  }, [items]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="border border-dashed border-border rounded-lg p-8 text-center">
        <FileText className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
        <p className="text-sm font-medium text-muted-foreground">No context items yet</p>
        <p className="text-xs text-muted-foreground mt-1">
          Select sources and run a sync to start building context.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {totalCount} item{totalCount !== 1 ? 's' : ''} synced
          {retainedCount > 0 && <> · {retainedCount} retained</>}
        </p>
      </div>

      {grouped.map(([resourceId, group]) => (
        <div key={resourceId} className="rounded-lg border border-border overflow-hidden">
          <div className="px-4 py-2 border-b border-border bg-muted/20">
            <p className="text-sm font-medium">{group.name}</p>
            <p className="text-xs text-muted-foreground">{group.items.length} item{group.items.length !== 1 ? 's' : ''}</p>
          </div>
          <div className="divide-y divide-border">
            {group.items.map((item) => (
              <div
                key={item.id}
                className={cn(
                  'px-4 py-3',
                  item.retained && 'bg-green-50/50 dark:bg-green-950/10'
                )}
              >
                <div className="flex items-start gap-2">
                  <p className="text-sm text-foreground/80 line-clamp-2 flex-1">{item.content}</p>
                  {item.retained && (
                    <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                      Retained
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  {item.source_timestamp && (
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(item.source_timestamp), { addSuffix: true })}
                    </span>
                  )}
                  {item.content_type && (
                    <>
                      {item.source_timestamp && <span className="text-xs text-muted-foreground">·</span>}
                      <span className="text-xs text-muted-foreground">{item.content_type}</span>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {items.length < totalCount && (
        <div className="flex justify-center pt-2">
          <button
            onClick={() => loadItems(items.length)}
            disabled={loadingMore}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm text-primary hover:text-primary/80 disabled:opacity-50"
          >
            {loadingMore ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Loading...
              </>
            ) : (
              <>Load more ({totalCount - items.length} remaining)</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
