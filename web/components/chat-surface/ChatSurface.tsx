'use client';

/**
 * ChatSurface — TP chat surface with TP-directed workspace state modal.
 *
 * ADR-167 v5 (2026-04-09) — layout restructured to match the surface shape
 * used by /work and /agents detail pages:
 *
 *   <PageHeader defaultLabel="Chat" />         — breadcrumb chrome
 *   <SurfaceIdentityHeader                     — the real h1 + actions
 *     title="Thinking Partner"
 *     actions={workspace-state toggle}
 *   />
 *   <ChatPanel />                              — conversation column
 *
 * The workspace-state toggle button (formerly an `inputRowAddon` crammed
 * inside the input row between the + menu and the textarea) moves up into
 * SurfaceIdentityHeader.actions where it sits alongside the page identity.
 * This matches /work detail's pattern where Run/Pause/Edit live in the
 * surface header, not in the chat input.
 *
 * ADR-165 v6 (2026-04-08): The workspace state surface is rendered as a
 * MODAL, not an inline overlay. TP is the single source of intent for when
 * it appears — frontend never auto-opens. The user can manually toggle via
 * the surface header button as an escape hatch.
 *
 * Marker pattern (modeled on ADR-162 inference-meta, unchanged from v5):
 *   <!-- workspace-state: {"lead":"empty","reason":"..."} -->
 *
 * The marker is parsed from the latest assistant message. When TP emits one,
 * the modal opens to the requested lead view. The marker is stripped from
 * the displayed message body in ChatPanel.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { LayoutPanelTop, Settings2 } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import { PageHeader } from '@/components/shell/PageHeader';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
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
  plusMenuActions: PlusMenuAction[];
  onContextSubmit: (message: string) => void;
}

export function ChatSurface({
  agents,
  tasks,
  dataLoading,
  plusMenuActions,
  onContextSubmit,
}: ChatSurfaceProps) {
  const { messages } = useTP();

  // Modal open state — controlled here, not by ChatPanel.
  const [open, setOpen] = useState(false);
  const [lead, setLead] = useState<WorkspaceStateLead | null>(null);
  const [reason, setReason] = useState<string | null>(null);

  // Track the last message id we processed for marker directives, so we
  // don't re-fire the modal every render.
  const [lastProcessedId, setLastProcessedId] = useState<string | null>(null);

  // Watch the latest assistant message for a workspace-state marker.
  // When present, open the modal with the requested lead view. This is the
  // ONLY automatic open path — there is no cold-start auto-open in v6.
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
  // surface, since ContextSetup is the modal's empty-lead view.
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

  // Workspace state toggle — lives in the surface header alongside the H1.
  // Replaces the earlier `inputRowAddon` pattern where it was crammed into
  // the chat input row.
  const workspaceStateAction = (
    <button
      type="button"
      onClick={handleToggle}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      title="Open workspace state"
    >
      <LayoutPanelTop className="w-3.5 h-3.5" />
      Workspace state
    </button>
  );

  // Workspace is "empty" when there are no tasks yet — used by the modal's
  // computeLead() fallback for manual opens. No frontend judgment about
  // whether to AUTO-open; TP owns that decision.
  const isEmpty = !dataLoading && tasks.length === 0;

  return (
    <div className="flex h-full flex-col bg-background">
      <PageHeader defaultLabel="Chat" />
      <SurfaceIdentityHeader
        title="Thinking Partner"
        actions={workspaceStateAction}
      />
      <div className="flex-1 min-h-0">
        <div className="mx-auto h-full w-full max-w-3xl px-4 py-5">
          <ChatPanel
            surfaceOverride={{ type: 'chat' }}
            plusMenuActions={augmentedPlusMenuActions}
            placeholder="Ask anything or type / ..."
            showCommandPicker={true}
            showInputDivider={false}
          />
        </div>
      </div>
      <WorkspaceStateView
        open={open}
        lead={lead}
        agents={agents}
        tasks={tasks}
        dataLoading={dataLoading}
        isEmpty={isEmpty}
        reason={reason}
        onClose={handleClose}
        onContextSubmit={(msg) => {
          onContextSubmit(msg);
          setOpen(false);
        }}
      />
    </div>
  );
}
