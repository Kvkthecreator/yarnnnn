'use client';

/**
 * ADR-020: Inline Tool Result Cards
 *
 * Renders rich inline cards for tool results in the chat.
 * Shows deliverable details, lists, and action confirmations.
 */

import { Calendar, Clock, CheckCircle2, PauseCircle, AlertCircle, FileText, Repeat, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolResultData } from '@/hooks/useChat';

interface ToolResultCardProps {
  result: ToolResultData;
  onNavigate?: (path: string) => void;
  onOpenTab?: (id: string, title: string) => void;
}

// Type-specific card data extractors
interface DeliverableData {
  id: string;
  title: string;
  type: string;
  schedule?: string;
  next_run?: string;
  recipient?: string;
  status?: string;
}

interface DeliverableListItem {
  id: string;
  title: string;
  type: string;
  status: string;
  schedule?: string;
  next_run?: string;
  version_count?: number;
  latest_version_status?: string;
}

export function ToolResultCard({ result, onNavigate, onOpenTab }: ToolResultCardProps) {
  const { toolName, success, data } = result;

  if (!success) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-destructive/10 text-destructive rounded-lg text-xs">
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>{(data as { error?: string })?.error || 'Action failed'}</span>
      </div>
    );
  }

  // Route to appropriate card based on tool name
  switch (toolName) {
    case 'create_deliverable':
      return <DeliverableCreatedCard data={data} onOpenTab={onOpenTab} />;
    case 'list_deliverables':
      return <DeliverableListCard data={data} onOpenTab={onOpenTab} />;
    case 'get_deliverable':
      return <DeliverableDetailCard data={data} onOpenTab={onOpenTab} />;
    case 'update_deliverable':
      return <DeliverableUpdatedCard data={data} />;
    case 'run_deliverable':
      return <DeliverableRunCard data={data} onOpenTab={onOpenTab} />;
    default:
      // Don't show card for unhandled tools
      return null;
  }
}

// Card for newly created deliverable
function DeliverableCreatedCard({
  data,
  onOpenTab,
}: {
  data: Record<string, unknown>;
  onOpenTab?: (id: string, title: string) => void;
}) {
  const deliverable = data.deliverable as DeliverableData | undefined;
  if (!deliverable) return null;

  return (
    <div
      className="border border-border rounded-lg p-3 bg-background/50 cursor-pointer hover:border-primary/50 transition-colors"
      onClick={() => onOpenTab?.(deliverable.id, deliverable.title)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4 text-primary" />
          </div>
          <div>
            <p className="font-medium text-sm">{deliverable.title}</p>
            <p className="text-xs text-muted-foreground">{deliverable.type}</p>
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
        {deliverable.schedule && (
          <span className="flex items-center gap-1">
            <Repeat className="w-3 h-3" />
            {deliverable.schedule}
          </span>
        )}
        {deliverable.next_run && (
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            Next: {formatDate(deliverable.next_run)}
          </span>
        )}
        {deliverable.recipient && (
          <span className="flex items-center gap-1">
            <Users className="w-3 h-3" />
            {deliverable.recipient}
          </span>
        )}
      </div>

      <p className="mt-2 text-xs text-primary">View in dashboard</p>
    </div>
  );
}

// Card for deliverable list
function DeliverableListCard({
  data,
  onOpenTab,
}: {
  data: Record<string, unknown>;
  onOpenTab?: (id: string, title: string) => void;
}) {
  const deliverables = data.deliverables as DeliverableListItem[] | undefined;
  const count = data.count as number | undefined;

  if (!deliverables || deliverables.length === 0) {
    return (
      <div className="text-xs text-muted-foreground italic">
        No deliverables found.
      </div>
    );
  }

  // Show first 3 deliverables
  const displayItems = deliverables.slice(0, 3);
  const hasMore = deliverables.length > 3;

  return (
    <div className="space-y-2">
      {displayItems.map((d) => (
        <div
          key={d.id}
          className="flex items-center gap-3 px-3 py-2 border border-border rounded-lg bg-background/50 cursor-pointer hover:border-primary/50 transition-colors"
          onClick={() => onOpenTab?.(d.id, d.title)}
        >
          <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
            <FileText className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm truncate">{d.title}</p>
            <p className="text-xs text-muted-foreground flex items-center gap-2">
              <span>{d.type}</span>
              <span className={cn(
                'px-1.5 py-0.5 rounded text-[10px] uppercase font-medium',
                d.status === 'active' && 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
                d.status === 'paused' && 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
              )}>
                {d.status}
              </span>
            </p>
          </div>
          {d.schedule && (
            <span className="text-xs text-muted-foreground hidden sm:block">
              {d.schedule}
            </span>
          )}
        </div>
      ))}

      {hasMore && (
        <p className="text-xs text-muted-foreground text-center">
          +{count! - 3} more
        </p>
      )}
    </div>
  );
}

// Card for deliverable detail view
function DeliverableDetailCard({
  data,
  onOpenTab,
}: {
  data: Record<string, unknown>;
  onOpenTab?: (id: string, title: string) => void;
}) {
  const deliverable = data.deliverable as DeliverableData | undefined;
  const versions = data.versions as Array<{ version_number: number; status: string; created_at: string }> | undefined;
  const versionCount = data.version_count as number | undefined;

  if (!deliverable) return null;

  return (
    <div
      className="border border-border rounded-lg p-3 bg-background/50 cursor-pointer hover:border-primary/50 transition-colors"
      onClick={() => onOpenTab?.(deliverable.id, deliverable.title)}
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
          <FileText className="w-5 h-5 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">{deliverable.title}</p>
          <p className="text-xs text-muted-foreground">{deliverable.type}</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Repeat className="w-3 h-3" />
          <span>{deliverable.schedule}</span>
        </div>
        {deliverable.next_run && (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Clock className="w-3 h-3" />
            <span>Next: {formatDate(deliverable.next_run)}</span>
          </div>
        )}
      </div>

      {versions && versions.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground mb-2">
            Recent versions ({versionCount})
          </p>
          <div className="space-y-1">
            {versions.slice(0, 2).map((v) => (
              <div key={v.version_number} className="flex items-center justify-between text-xs">
                <span>v{v.version_number}</span>
                <span className={cn(
                  'px-1.5 py-0.5 rounded text-[10px] uppercase font-medium',
                  v.status === 'approved' && 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
                  v.status === 'staged' && 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
                  v.status === 'draft' && 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
                )}>
                  {v.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="mt-2 text-xs text-primary">View details</p>
    </div>
  );
}

// Card for updated deliverable
function DeliverableUpdatedCard({ data }: { data: Record<string, unknown> }) {
  const deliverable = data.deliverable as { title?: string; status?: string } | undefined;
  const message = data.message as string | undefined;

  if (!deliverable) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg bg-background/50">
      {deliverable.status === 'paused' ? (
        <PauseCircle className="w-4 h-4 text-yellow-500" />
      ) : (
        <CheckCircle2 className="w-4 h-4 text-green-500" />
      )}
      <span className="text-sm">
        {message || `"${deliverable.title}" ${deliverable.status}`}
      </span>
    </div>
  );
}

// Card for triggered deliverable run
function DeliverableRunCard({
  data,
  onOpenTab,
}: {
  data: Record<string, unknown>;
  onOpenTab?: (id: string, title: string) => void;
}) {
  const deliverableId = data.deliverable_id as string | undefined;
  const deliverableTitle = data.deliverable_title as string | undefined;
  const versionNumber = data.version_number as number | undefined;
  const message = data.message as string | undefined;

  return (
    <div
      className="flex items-center gap-3 px-3 py-2 border border-border rounded-lg bg-background/50 cursor-pointer hover:border-primary/50 transition-colors"
      onClick={() => deliverableId && onOpenTab?.(deliverableId, deliverableTitle || 'Deliverable')}
    >
      <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center animate-pulse">
        <Clock className="w-4 h-4 text-blue-600 dark:text-blue-400" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium">Generating v{versionNumber || '?'}</p>
        <p className="text-xs text-muted-foreground">{message || 'Check dashboard for status'}</p>
      </div>
    </div>
  );
}

// Helper to format dates
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays < 7) {
      return date.toLocaleDateString('en-US', { weekday: 'long' });
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}
