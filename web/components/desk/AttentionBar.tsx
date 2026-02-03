'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Attention bar - shows staged items needing review
 */

import { Clock } from 'lucide-react';
import { AttentionItem } from '@/types/desk';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow } from 'date-fns';

interface AttentionBarProps {
  items: AttentionItem[];
}

export function AttentionBar({ items }: AttentionBarProps) {
  const { setSurface, surface } = useDesk();

  if (items.length === 0) return null;

  return (
    <div className="shrink-0 border-t border-border bg-muted/30 px-4 py-2">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Clock className="w-3.5 h-3.5" />
          <span>{items.length} need{items.length === 1 ? 's' : ''} review</span>
        </div>

        <div className="flex gap-2 overflow-x-auto scrollbar-hide">
          {items.map((item) => {
            const isActive =
              surface.type === 'deliverable-review' && surface.versionId === item.versionId;

            return (
              <button
                key={item.versionId}
                onClick={() =>
                  setSurface({
                    type: 'deliverable-review',
                    deliverableId: item.deliverableId,
                    versionId: item.versionId,
                  })
                }
                className={`
                  shrink-0 px-3 py-1 text-xs border rounded-full whitespace-nowrap
                  transition-colors
                  ${
                    isActive
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border hover:bg-background hover:border-primary/50'
                  }
                `}
              >
                <span>{item.title}</span>
                <span className="ml-1.5 text-[10px] opacity-70">
                  {formatDistanceToNow(new Date(item.stagedAt), { addSuffix: false })}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
