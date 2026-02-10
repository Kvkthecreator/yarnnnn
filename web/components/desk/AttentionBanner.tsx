'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 *
 * AttentionBanner - Surfaces attention items in the chat-first experience
 * Displayed at top of chat when items need user review
 */

import { Bell, ChevronRight } from 'lucide-react';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

export function AttentionBanner() {
  const { attention, setSurface } = useDesk();

  if (attention.length === 0) return null;

  const handleReview = (item: typeof attention[0]) => {
    setSurface({
      type: 'deliverable-review',
      deliverableId: item.deliverableId,
      versionId: item.versionId,
    });
  };

  // Show first item prominently, rest as count
  const [first, ...rest] = attention;

  return (
    <div className="border-b border-border bg-amber-50 dark:bg-amber-950/20 px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-amber-100 dark:bg-amber-900/30">
          <Bell className="w-4 h-4 text-amber-600 dark:text-amber-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
            {attention.length === 1
              ? 'Ready for review'
              : `${attention.length} items ready for review`}
          </p>
          <p className="text-xs text-amber-700 dark:text-amber-300 truncate">
            {first.title} · staged {formatDistanceToNow(new Date(first.stagedAt), { addSuffix: true })}
          </p>
        </div>
        <button
          onClick={() => handleReview(first)}
          className={cn(
            'flex items-center gap-1 px-3 py-1.5 rounded-md text-sm font-medium',
            'bg-amber-600 text-white hover:bg-amber-700 transition-colors'
          )}
        >
          Review
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Show additional items if more than one */}
      {rest.length > 0 && (
        <div className="mt-2 pt-2 border-t border-amber-200 dark:border-amber-800">
          <div className="flex flex-wrap gap-2">
            {rest.slice(0, 3).map((item) => (
              <button
                key={item.versionId}
                onClick={() => handleReview(item)}
                className="text-xs px-2 py-1 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors truncate max-w-[150px]"
              >
                {item.title}
              </button>
            ))}
            {rest.length > 3 && (
              <span className="text-xs text-amber-600 dark:text-amber-400 px-2 py-1">
                +{rest.length - 3} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
