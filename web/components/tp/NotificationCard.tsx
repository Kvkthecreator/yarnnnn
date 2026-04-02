/**
 * ADR-155: Inline notification card for tool side effects.
 *
 * Rendered in the chat stream when a tool result has a user-visible
 * side effect (workspace scaffolded, task created, etc.).
 */

import { Sparkles, ListChecks, CheckCircle2, BookmarkPlus } from 'lucide-react';

const ICONS: Record<string, typeof Sparkles> = {
  UpdateContext: Sparkles,
  CreateTask: ListChecks,
  ManageTask: CheckCircle2,
};

interface NotificationCardProps {
  title: string;
  description?: string;
  toolName: string;
}

export function NotificationCard({ title, description, toolName }: NotificationCardProps) {
  const Icon = ICONS[toolName] || BookmarkPlus;

  return (
    <div className="flex items-start gap-2 p-2.5 rounded-lg border border-border bg-muted/30 my-1 animate-in fade-in slide-in-from-bottom-1 duration-150">
      <Icon className="w-3.5 h-3.5 text-primary mt-0.5 shrink-0" />
      <div className="min-w-0">
        <p className="text-xs font-medium">{title}</p>
        {description && (
          <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
            {description}
          </p>
        )}
      </div>
    </div>
  );
}
