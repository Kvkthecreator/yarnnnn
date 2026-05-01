/**
 * ADR-179: System event cards — pre-composed assistant messages persisted as
 * session_messages rows with metadata.system_card set. Zero LLM cost.
 * TP reads the content field as conversation history; frontend renders the card.
 *
 * ADR-219 Commit 5: adds the `narrative_digest` card written by
 * back-office-narrative-digest. Renders as a collapsed-by-default
 * roll-up with expand-to-list using metadata.rolled_up_count + counts.
 */

import { useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, Layers, ListCollapse } from 'lucide-react';
import type { SystemCardType } from '@/types/desk';

interface WorkspaceInitCompleteData {
  system_card: 'workspace_init_complete';
  agents_created?: number;
  tasks_created?: string[];
}

interface TaskCompleteData {
  system_card: 'task_complete';
  task_slug?: string;
  task_title?: string;
  output_path?: string;
  run_at?: string;
}

interface NarrativeDigestData {
  system_card: 'narrative_digest';
  rolled_up_count?: number;
  rolled_up_window_hours?: number;
  rolled_up_ids?: string[];
  counts?: { material?: number; routine?: number; housekeeping?: number };
  summary?: string;
  // The raw body text (passed via metadata.summary on the rollup entry —
  // see services/back_office/narrative_digest.py::_format_digest_body)
  // is the full bullet list. We expose it through the SystemCard
  // wrapper's `content` plumbing rather than re-deriving here.
}

type SystemCardData =
  | WorkspaceInitCompleteData
  | TaskCompleteData
  | NarrativeDigestData
  | Record<string, unknown>;

interface SystemCardProps {
  card_type: SystemCardType;
  data: SystemCardData;
}

function WorkspaceInitCard({ data }: { data: WorkspaceInitCompleteData }) {
  const agentCount = data.agents_created ?? 9;
  const taskCount = data.tasks_created?.length ?? 3;

  return (
    <div className="flex items-start gap-2.5 p-3 rounded-lg border border-border bg-muted/30 my-1 animate-in fade-in slide-in-from-bottom-1 duration-150">
      <CheckCircle2 className="w-4 h-4 text-primary mt-0.5 shrink-0" />
      <div className="min-w-0 space-y-0.5">
        <p className="text-xs font-medium">Workspace ready</p>
        <p className="text-[11px] text-muted-foreground">
          {agentCount} agents · {taskCount} tasks scheduled · daily update at 9am
        </p>
      </div>
    </div>
  );
}

function TaskCompleteCard({ data }: { data: TaskCompleteData }) {
  const title = data.task_title || data.task_slug || 'Task';
  // Link to the output file in the Files explorer (path-based, stays in context).
  // ADR-231 D2 natural-home: reports live at /workspace/reports/{slug}/.
  const outputPath = data.output_path
    || (data.task_slug ? `/workspace/reports/${data.task_slug}` : null);
  const href = outputPath
    ? `/context?path=${encodeURIComponent(outputPath)}`
    : '/context';

  return (
    <div className="flex items-center justify-between gap-2.5 p-3 rounded-lg border border-border bg-muted/30 my-1 animate-in fade-in slide-in-from-bottom-1 duration-150">
      <div className="flex items-center gap-2.5 min-w-0">
        <Layers className="w-4 h-4 text-primary shrink-0" />
        <div className="min-w-0">
          <p className="text-xs font-medium truncate">{title} finished</p>
          {data.run_at && (
            <p className="text-[11px] text-muted-foreground">
              {new Date(data.run_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </p>
          )}
        </div>
      </div>
      <Link
        href={href}
        className="text-[11px] text-primary hover:underline shrink-0 font-medium"
      >
        Open →
      </Link>
    </div>
  );
}

function NarrativeDigestCard({ data }: { data: NarrativeDigestData & { _body?: string } }) {
  const [expanded, setExpanded] = useState(false);
  const count = data.rolled_up_count ?? 0;
  const window = data.rolled_up_window_hours ?? 24;
  const headline = count > 0
    ? `${count} housekeeping invocations rolled up — all clean`
    : 'Housekeeping rollup — nothing to report';

  // Body bullets live in the original message content (passed via _body).
  // Format: a few prose lines + bulleted summaries. Show on expand.
  const body = data._body ?? '';

  return (
    <div className="rounded-lg border border-border bg-muted/30 my-1 animate-in fade-in slide-in-from-bottom-1 duration-150 overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-start gap-2.5 p-3 text-left hover:bg-muted/50 transition-colors"
        aria-expanded={expanded}
      >
        <ListCollapse className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium">{headline}</p>
          <p className="text-[11px] text-muted-foreground">
            Last {window}h
            {data.counts && (
              <>
                {' · '}
                {data.counts.material ?? 0} material
                {' · '}
                {data.counts.routine ?? 0} routine
                {' · '}
                {data.counts.housekeeping ?? 0} housekeeping
              </>
            )}
          </p>
        </div>
        <span className="text-[10px] text-muted-foreground/70 shrink-0">
          {expanded ? 'Hide' : 'Show'}
        </span>
      </button>
      {expanded && body && (
        <div className="px-3 pb-3 pt-0 border-t border-border/40 bg-background/30">
          <pre className="text-[11px] text-muted-foreground whitespace-pre-wrap font-sans leading-relaxed">
            {body}
          </pre>
        </div>
      )}
    </div>
  );
}

export function SystemCard({ card_type, data }: SystemCardProps) {
  if (card_type === 'workspace_init_complete') {
    return <WorkspaceInitCard data={data as WorkspaceInitCompleteData} />;
  }
  if (card_type === 'task_complete') {
    return <TaskCompleteCard data={data as TaskCompleteData} />;
  }
  if (card_type === 'narrative_digest') {
    return <NarrativeDigestCard data={data as NarrativeDigestData & { _body?: string }} />;
  }
  return null;
}
