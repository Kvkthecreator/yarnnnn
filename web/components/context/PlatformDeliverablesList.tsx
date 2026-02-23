'use client';

import { useRouter } from 'next/navigation';
import { Plus, Sparkles } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { PlatformDeliverable } from '@/types';
import { StatusBadge } from './StatusBadge';

interface PlatformDeliverablesListProps {
  platform: string;
  platformLabel: string;
  deliverables: PlatformDeliverable[];
}

export function PlatformDeliverablesList({
  platform,
  platformLabel,
  deliverables,
}: PlatformDeliverablesListProps) {
  const router = useRouter();

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold">Deliverables → {platformLabel}</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Scheduled outputs targeting {platformLabel}.
          </p>
        </div>
        <button
          onClick={() => router.push(`/deliverables/new?platform=${platform}`)}
          className="text-sm text-primary hover:underline flex items-center gap-1 shrink-0"
        >
          <Plus className="w-3 h-3" />
          New deliverable
        </button>
      </div>

      {deliverables.length === 0 ? (
        <div className="border border-dashed border-border rounded-lg p-8 text-center">
          <p className="text-sm text-muted-foreground mb-3">
            No deliverables targeting {platformLabel} yet.
          </p>
          <button
            onClick={() => router.push(`/deliverables/new?platform=${platform}`)}
            className="text-sm text-primary hover:underline"
          >
            Create your first
          </button>
        </div>
      ) : (
        <div className="border border-border rounded-lg divide-y divide-border">
          {deliverables.map((deliverable) => (
            <button
              key={deliverable.id}
              onClick={() => router.push(`/deliverables/${deliverable.id}`)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors text-left"
            >
              <div>
                <p className="text-sm font-medium">{deliverable.title}</p>
                <p className="text-xs text-muted-foreground capitalize">
                  {deliverable.deliverable_type.replace(/_/g, ' ')}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={deliverable.status} />
                {deliverable.next_run_at && (
                  <span className="text-xs text-muted-foreground">
                    Next: {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })}
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
