'use client';

/**
 * ADR-036/037: Two-Layer + Chat-First Architecture
 *
 * AttentionBanner - Subtle inline notification for items needing review
 *
 * Design philosophy (per ADR-036):
 * - Interaction Layer is fluid and emergent
 * - Notifications should be subtle, not alarm-like
 * - Review items are part of the normal flow, not interruptions
 */

import { FileCheck, ChevronRight } from 'lucide-react';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow } from 'date-fns';

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
    <div className="px-4 py-2 border-b border-border">
      <div className="flex items-center gap-2 text-sm">
        <FileCheck className="w-4 h-4 text-primary shrink-0" />
        <button
          onClick={() => handleReview(first)}
          className="flex items-center gap-1 text-primary hover:underline truncate"
        >
          <span className="truncate">{first.title}</span>
          <span className="text-muted-foreground shrink-0">
            · {formatDistanceToNow(new Date(first.stagedAt), { addSuffix: true })}
          </span>
        </button>
        {rest.length > 0 && (
          <span className="text-muted-foreground shrink-0">
            +{rest.length} more
          </span>
        )}
        <ChevronRight className="w-4 h-4 text-muted-foreground ml-auto shrink-0" />
      </div>
    </div>
  );
}
