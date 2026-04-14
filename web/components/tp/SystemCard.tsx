/**
 * ADR-179: System event cards — pre-composed assistant messages persisted as
 * session_messages rows with metadata.system_card set. Zero LLM cost.
 * TP reads the content field as conversation history; frontend renders the card.
 */

import Link from 'next/link';
import { CheckCircle2, Layers } from 'lucide-react';
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

type SystemCardData = WorkspaceInitCompleteData | TaskCompleteData | Record<string, unknown>;

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
  const href = data.task_slug ? `/work?task=${data.task_slug}` : '/work';

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
        View →
      </Link>
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
  return null;
}
