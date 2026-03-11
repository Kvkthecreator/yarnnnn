'use client';

/**
 * YARNNN Context Page (ADR-102)
 *
 * Shows agent outputs stored as platform_content with platform="yarnnn".
 * Unlike other context pages, yarnnn has no OAuth connection, no source selection,
 * and no sync — content is written internally after each successful delivery.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Globe,
  Loader2,
  FileText,
  Clock,
  Shield,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { PlatformContentItem } from '@/types';

export default function YarnnnContextPage() {
  const router = useRouter();
  const [items, setItems] = useState<PlatformContentItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const loadItems = async (offset = 0) => {
    if (offset === 0) setLoading(true);
    else setLoadingMore(true);

    try {
      const result = await api.integrations.getPlatformContext('yarnnn', {
        limit: 20,
        offset,
      });
      if (offset === 0) {
        setItems(result.items || []);
      } else {
        setItems((prev) => [...prev, ...(result.items || [])]);
      }
      setTotalCount(result.total_count || 0);
    } catch {
      // yarnnn content may not exist yet
      if (offset === 0) setItems([]);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    loadItems();
  }, []);

  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background border-b border-border">
        <div className="px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => router.push('/context')}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className={cn(
            "flex items-center justify-center w-8 h-8 rounded-lg",
            "bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400"
          )}>
            <Globe className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Generated Content</h1>
            <p className="text-xs text-muted-foreground">
              Agent outputs stored as searchable context
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Summary stats */}
        <div className="flex items-center gap-6 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" />
            {totalCount} {totalCount === 1 ? 'item' : 'items'}
          </span>
          <span className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5" />
            Always retained
          </span>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Empty state */}
        {!loading && items.length === 0 && (
          <div className="text-center py-16 space-y-3">
            <Globe className="w-10 h-10 text-muted-foreground/40 mx-auto" />
            <div>
              <p className="text-sm font-medium text-foreground">No generated content yet</p>
              <p className="text-xs text-muted-foreground mt-1">
                Agent outputs will appear here after their first successful delivery.
              </p>
            </div>
          </div>
        )}

        {/* Content feed */}
        {!loading && items.length > 0 && (
          <div className="space-y-3">
            {items.map((item) => (
              <div
                key={item.id}
                className="border border-border rounded-lg p-4 bg-card hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {item.resource_name && (
                        <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
                          {item.resource_name}
                        </span>
                      )}
                      {item.content_type && (
                        <span className="text-xs text-muted-foreground px-1.5 py-0.5 bg-muted rounded">
                          {item.content_type}
                        </span>
                      )}
                      {'version_number' in (item.metadata || {}) && (
                        <span className="text-xs text-muted-foreground">
                          v{String(item.metadata.version_number)}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-foreground line-clamp-3">
                      {item.content.slice(0, 300)}
                      {item.content.length > 300 && '...'}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground shrink-0">
                    <Clock className="w-3 h-3" />
                    {item.source_timestamp
                      ? formatDistanceToNow(new Date(item.source_timestamp), { addSuffix: true })
                      : formatDistanceToNow(new Date(item.fetched_at), { addSuffix: true })}
                  </div>
                </div>
              </div>
            ))}

            {/* Load more */}
            {items.length < totalCount && (
              <button
                onClick={() => loadItems(items.length)}
                disabled={loadingMore}
                className="w-full py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {loadingMore ? (
                  <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                ) : (
                  `Load more (${totalCount - items.length} remaining)`
                )}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
