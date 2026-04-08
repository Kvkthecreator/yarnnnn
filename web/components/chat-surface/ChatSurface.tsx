'use client';

/**
 * ChatSurface — TP chat surface with on-demand workspace state view.
 *
 * ADR-165 v5: One single workspace state surface, opened by TP via marker
 * directives or by the user via the input-row icon. No always-on artifact
 * tabs. The page is TP chat — workspace state is a tool TP reaches for when
 * relevant, not a permanent dashboard above the conversation.
 *
 * Marker pattern (ADR-165 v5, modeled on ADR-162 inference-meta):
 *   <!-- workspace-state: {"lead":"empty","reason":"..."} -->
 *
 * The marker is parsed from the latest assistant message. When TP emits one,
 * the surface auto-opens to the requested lead view. The marker is stripped
 * from the displayed message body in ChatPanel.
 *
 * Manual override: the input-row icon toggles the surface. On manual open,
 * the lead is computed deterministically from current data — TP is not
 * called for manual opens.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { LayoutPanelTop, Settings2 } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import type { Agent, Task } from '@/types';
import { useTP } from '@/contexts/TPContext';
import {
  parseWorkspaceStateMeta,
  type WorkspaceStateLead,
} from '@/lib/workspace-state-meta';
import { WorkspaceStateView } from './WorkspaceStateView';

interface ChatSurfaceProps {
  agents: Agent[];
  tasks: Task[];
  dataLoading: boolean;
  isNewUser: boolean;
  plusMenuActions: PlusMenuAction[];
  onContextSubmit: (message: string) => void;
}

const CHAT_EMPTY_STATE = (
  <div className="px-4 py-5 text-center">
    <p className="text-sm font-medium">TP is here.</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Ask for a readout, a new task, or what needs attention.
    </p>
  </div>
);

export function ChatSurface({
  agents,
  tasks,
  dataLoading,
  isNewUser,
  plusMenuActions,
  onContextSubmit,
}: ChatSurfaceProps) {
  const { messages } = useTP();

  // Surface open state — controlled here, not by ChatPanel.
  const [open, setOpen] = useState(false);
  const [lead, setLead] = useState<WorkspaceStateLead | null>(null);
  const [reason, setReason] = useState<string | null>(null);

  // Track the last message id we processed for marker directives, so we
  // don't re-fire the surface every render.
  const [lastProcessedId, setLastProcessedId] = useState<string | null>(null);

  // Cold-start: if the workspace is empty AND there are no messages yet,
  // auto-open the surface to the empty lead. This is the gate behavior —
  // TP hasn't had a chance to emit a marker yet because no message has
  // been sent. Once TP responds, it owns the surface.
  useEffect(() => {
    if (isNewUser && messages.length === 0 && !open) {
      setOpen(true);
      setLead('empty');
      setReason(null);
    }
  }, [isNewUser, messages.length, open]);

  // Watch the latest assistant message for a workspace-state marker.
  // When present, open the surface with the requested lead view.
  useEffect(() => {
    if (messages.length === 0) return;
    const latest = messages[messages.length - 1];
    if (latest.role !== 'assistant') return;
    if (latest.id === lastProcessedId) return;
    if (!latest.content) return;

    const { directive } = parseWorkspaceStateMeta(latest.content);
    setLastProcessedId(latest.id);
    if (!directive) return;

    setOpen(true);
    setLead(directive.lead);
    setReason(directive.reason ?? null);
  }, [messages, lastProcessedId]);

  const handleToggle = useCallback(() => {
    setOpen((prev) => {
      if (prev) return false;
      // Manual open: deterministic lead, no TP call.
      setLead(null); // null tells WorkspaceStateView to compute from data
      setReason(null);
      return true;
    });
  }, []);

  const openWithLead = useCallback((nextLead: WorkspaceStateLead, nextReason?: string) => {
    setOpen(true);
    setLead(nextLead);
    setReason(nextReason ?? null);
  }, []);

  const handleClose = useCallback(() => setOpen(false), []);

  // Inject "Update my context" as the first plus-menu action — owned by the
  // surface, since ContextSetup is the surface's empty-lead view.
  const augmentedPlusMenuActions: PlusMenuAction[] = useMemo(() => {
    const updateAction: PlusMenuAction = {
      id: 'update-context',
      label: 'Update my context',
      icon: Settings2,
      verb: 'show',
      onSelect: () => openWithLead('empty', 'Add to your workspace context'),
    };
    return [updateAction, ...plusMenuActions];
  }, [plusMenuActions, openWithLead]);

  const inputRowAddon = useMemo(
    () => (
      <button
        type="button"
        onClick={handleToggle}
        className="shrink-0 p-2.5 text-muted-foreground hover:text-foreground transition-colors"
        aria-label="Toggle workspace state"
        title="Workspace state"
      >
        <LayoutPanelTop className="h-4 w-4" />
      </button>
    ),
    [handleToggle],
  );

  const surfaceContent = (
    <div className="mx-auto w-full max-w-3xl">
      <WorkspaceStateView
        open={open}
        lead={lead}
        agents={agents}
        tasks={tasks}
        dataLoading={dataLoading}
        isEmpty={isNewUser}
        reason={reason}
        onClose={handleClose}
        onContextSubmit={(msg) => {
          onContextSubmit(msg);
          setOpen(false);
        }}
      />
    </div>
  );

  return (
    <div className="h-full bg-background">
      <div className="mx-auto h-full w-full max-w-3xl px-4 py-5">
        <ChatPanel
          surfaceOverride={{ type: 'chat' }}
          plusMenuActions={augmentedPlusMenuActions}
          placeholder="Ask anything or type / ..."
          showCommandPicker={true}
          emptyState={CHAT_EMPTY_STATE}
          topContent={open ? surfaceContent : null}
          showInputDivider={false}
          inputRowAddon={inputRowAddon}
        />
      </div>
    </div>
  );
}
