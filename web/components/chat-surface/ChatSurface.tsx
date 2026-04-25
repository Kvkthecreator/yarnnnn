'use client';

/**
 * ChatSurface — YARNNN chat surface (ADR-165 v8, ADR-189, ADR-190, ADR-215 Phases 5 + 6).
 *
 *   <SurfaceIdentityHeader title="YARNNN" actions={Snapshot toggle} />
 *   <ChatPanel emptyState={<ChatEmptyState onChipClick={seedComposer} />} />
 *
 * Two sibling modals, opened independently:
 *   1. SnapshotModal — mid-conversation awareness overlay (three tabs:
 *      Mandate / Review standard / Recent). Opened by YARNNN-emitted
 *      `<!-- snapshot: ... -->` marker or the surface header "Snapshot"
 *      button. Pure read, zero LLM at open, stay-in-chat contract per
 *      ADR-215 Phase 6.
 *   2. TaskSetupModal — structured task creation (wraps TaskSetup).
 *      Opened by "Start new work" plus-menu action or Heads Up idle-agents flag.
 *
 * ADR-215 Phase 6 (2026-04-24): the overlay prior named "Workspace" with
 *   four tabs (Readiness / Attention / Last session / Activity) reframed as
 *   "Snapshot" with three tabs — a Briefing archetype that renders content
 *   in place rather than shipping the operator to other tabs. Marker renamed
 *   workspace-state → snapshot.
 *
 * ADR-215 Phase 5 (2026-04-24): OnboardingModal / ContextSetup retired.
 * ADR-190 (2026-04-17): onboarding is conversational with YARNNN.
 * ADR-178 (2026-04-13): TaskSetup added as the singular creation modal.
 * ADR-189 (2026-04-17): TP → YARNNN user-facing rename.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { LayoutDashboard, ListChecks, Filter } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import type { Task } from '@/types';
import { useTP } from '@/contexts/TPContext';
import {
  parseSnapshotMeta,
  type SnapshotLead,
} from '@/lib/snapshot-meta';
import { SnapshotModal } from './SnapshotModal';
import { TaskSetupModal } from './TaskSetupModal';
import { ChatEmptyState } from './ChatEmptyState';
import { ChatFilterBar, parseChatFilterFromSearch } from './ChatFilterBar';
import { cn } from '@/lib/utils';

interface ChatSurfaceProps {
  /** Tasks feed the Snapshot overlay's Recent tab (last-run list). */
  tasks: Task[];
  /** Additional plus-menu actions from the page. ChatSurface prepends its own built-in actions. */
  plusMenuActions?: PlusMenuAction[];
}

export function ChatSurface({
  tasks,
  plusMenuActions = [],
}: ChatSurfaceProps) {
  const { messages, sendMessage } = useTP();
  const searchParams = useSearchParams();

  // --- Snapshot overlay state ---
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotLead, setSnapshotLead] = useState<SnapshotLead | null>(null);
  const [snapshotReason, setSnapshotReason] = useState<string | null>(null);

  // --- Task setup modal state ---
  const [taskSetupOpen, setTaskSetupOpen] = useState(false);
  const [taskSetupInitialNotes, setTaskSetupInitialNotes] = useState('');

  // ADR-219 Commit 5: filter bar visibility (off by default — we
  // toggle from the surface header). The filter itself is parsed from
  // the URL each render so deep-links round-trip cleanly.
  const [filterBarOpen, setFilterBarOpen] = useState(false);
  const narrativeFilter = useMemo(() => {
    const params = new URLSearchParams(searchParams.toString());
    return parseChatFilterFromSearch(params);
  }, [searchParams]);

  // Auto-open the bar when any filter is active so the user can see
  // and clear them.
  useEffect(() => {
    if (narrativeFilter) setFilterBarOpen(true);
  }, [narrativeFilter]);

  // --- Empty-state chip seed (ADR-190) ---
  const [chipSeed, setChipSeed] = useState<{ id: string; text: string } | null>(null);
  const handleChipClick = useCallback((text: string) => {
    setChipSeed({ id: `chip-${Date.now()}`, text });
  }, []);

  // Track the last message id we processed for marker directives.
  const [lastProcessedId, setLastProcessedId] = useState<string | null>(null);

  // Watch the latest assistant message for the snapshot marker. ADR-215
  // Phase 6 renamed workspace-state → snapshot with a new three-value
  // lead enum (mandate | review | recent).
  useEffect(() => {
    if (messages.length === 0) return;
    const latest = messages[messages.length - 1];
    if (latest.role !== 'assistant') return;
    if (latest.id === lastProcessedId) return;
    if (!latest.content) return;

    setLastProcessedId(latest.id);

    const { directive } = parseSnapshotMeta(latest.content);
    if (directive) {
      setSnapshotOpen(true);
      setSnapshotLead(directive.lead);
      setSnapshotReason(directive.reason ?? null);
    }
  }, [messages, lastProcessedId]);

  // Manual Snapshot toggle — opens if closed, closes if open.
  const handleSnapshotToggle = useCallback(() => {
    setSnapshotOpen((prev) => {
      if (prev) return false;
      // Manual open: default tab (mandate), no YARNNN call.
      setSnapshotLead(null);
      setSnapshotReason(null);
      return true;
    });
  }, []);

  const handleSnapshotClose = useCallback(() => setSnapshotOpen(false), []);

  // Ask YARNNN (invoked by SnapshotModal's EditInChatButton seeders).
  const handleAskYARNNN = useCallback(
    (prompt: string) => {
      setSnapshotOpen(false);
      sendMessage(prompt);
    },
    [sendMessage],
  );

  // Task setup modal — opened from plus-menu.
  const handleOpenTaskSetup = useCallback((initialNotes = '') => {
    setSnapshotOpen(false);
    setTaskSetupInitialNotes(initialNotes);
    setTaskSetupOpen(true);
  }, []);

  // ADR-219 D6: "Make this recurring" graduates an inline operator
  // ask into a task. We open TaskSetupModal pre-filled with the
  // operator's original message so they confirm + refine; YARNNN
  // then calls ManageTask(action='create').
  const handleMakeRecurring = useCallback(
    (messageContent: string) => {
      const seed = messageContent.length > 480
        ? messageContent.slice(0, 480) + '…'
        : messageContent;
      handleOpenTaskSetup(`Recurring intent: ${seed}`);
    },
    [handleOpenTaskSetup],
  );

  const handleTaskSetupClose = useCallback(() => setTaskSetupOpen(false), []);

  const handleTaskSetupSubmit = useCallback(
    (msg: string) => {
      setTaskSetupOpen(false);
      sendMessage(msg);
    },
    [sendMessage],
  );

  // Built-in plus-menu actions — prepended to any page-supplied actions.
  // ADR-215 R4: + menu is a modal launcher only. Exactly one built-in —
  // "Start new work" → TaskSetupModal.
  const allPlusMenuActions = useMemo<PlusMenuAction[]>(() => [
    {
      id: 'create-task',
      label: 'Start new work',
      icon: ListChecks,
      verb: 'show',
      onSelect: () => handleOpenTaskSetup(),
    },
    ...plusMenuActions,
  ], [plusMenuActions, handleOpenTaskSetup]);

  // Snapshot toggle button — lives in the surface header.
  const snapshotAction = (
    <button
      type="button"
      onClick={handleSnapshotToggle}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      title="Open Snapshot"
    >
      <LayoutDashboard className="w-3.5 h-3.5" />
      Snapshot
    </button>
  );

  // ADR-219 Commit 5: filter bar toggle.
  const filterToggleAction = (
    <button
      type="button"
      onClick={() => setFilterBarOpen(v => !v)}
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1.5 text-xs font-medium rounded border transition-colors',
        narrativeFilter || filterBarOpen
          ? 'border-primary/40 bg-primary/5 text-primary'
          : 'border-border text-muted-foreground hover:text-foreground hover:bg-muted',
      )}
      title="Filter narrative"
      aria-pressed={filterBarOpen}
    >
      <Filter className="w-3.5 h-3.5" />
    </button>
  );

  const headerActions = (
    <div className="flex items-center gap-1.5">
      {filterToggleAction}
      {snapshotAction}
    </div>
  );

  const surfaceLogo = (
    <img
      src="/assets/logos/circleonly_yarnnn_1.svg"
      alt=""
      className="w-5 h-5"
    />
  );

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="mx-auto w-full max-w-3xl px-3 sm:px-4">
        <SurfaceIdentityHeader
          size="md"
          bordered={false}
          icon={surfaceLogo}
          title="yarnnn"
          brandTitle
          actions={headerActions}
        />
      </div>
      {filterBarOpen && (
        <div className="mx-auto w-full max-w-3xl">
          <ChatFilterBar />
        </div>
      )}
      <div className="flex-1 min-h-0">
        <div className="mx-auto h-full w-full max-w-3xl px-3 sm:px-4 py-3 sm:py-5">
          <ChatPanel
            surfaceOverride={{ type: 'chat' }}
            plusMenuActions={allPlusMenuActions}
            placeholder="Type, drop a file, or paste a link..."
            showCommandPicker={true}
            showInputDivider={false}
            draftSeed={chipSeed}
            narrativeFilter={narrativeFilter}
            onMakeRecurring={handleMakeRecurring}
            emptyState={(helpers) => (
              <ChatEmptyState
                onChipClick={handleChipClick}
                onUploadClick={helpers.requestUpload}
              />
            )}
          />
        </div>
      </div>

      {/* Snapshot overlay — Briefing archetype, pure read, zero LLM at open */}
      <SnapshotModal
        open={snapshotOpen}
        lead={snapshotLead}
        reason={snapshotReason}
        tasks={tasks}
        onClose={handleSnapshotClose}
        onAskTP={handleAskYARNNN}
      />

      {/* Task setup modal — structured task creation (ADR-178) */}
      <TaskSetupModal
        open={taskSetupOpen}
        onClose={handleTaskSetupClose}
        onSubmit={handleTaskSetupSubmit}
        initialNotes={taskSetupInitialNotes}
      />
    </div>
  );
}
