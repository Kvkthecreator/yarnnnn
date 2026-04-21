'use client';

/**
 * ChatSurface — YARNNN chat surface (ADR-165 v8, ADR-189, ADR-190).
 *
 *   <SurfaceIdentityHeader title="YARNNN" actions={Overview toggle} />
 *   <ChatPanel emptyState={<ChatEmptyState onChipClick={seedComposer} />} />
 *
 * Three sibling modals, opened independently:
 *   1. WorkspaceStateView (Overview) — read-only diagnostic dashboard
 *      Opened by: YARNNN `<!-- workspace-state: ... -->` marker or user "Overview" button
 *   2. OnboardingModal — first-run identity capture (wraps ContextSetup)
 *      Opened by: YARNNN `<!-- onboarding -->` marker only (auto-trigger sunsets in ADR-190 commit 2)
 *   3. TaskSetupModal — structured task creation (wraps TaskSetup)
 *      Opened by: "Start new work" plus-menu action or Heads Up idle-agents flag
 *
 * ADR-165 v8 (2026-04-09): Onboarding split from workspace state.
 * ADR-178 (2026-04-13): TaskSetup added as third modal.
 * ADR-189 (2026-04-17): TP → YARNNN user-facing rename.
 * ADR-190 (2026-04-17): Empty state renders ChatEmptyState — deterministic
 *   client-side welcome + 4 chips prompting rich-input behaviors. Replaces
 *   prior silent-canvas empty state. Zero LLM cost on first load.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { LayoutDashboard, ListChecks, SlidersHorizontal } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import type { Agent, Task } from '@/types';
import { useTP } from '@/contexts/TPContext';
import {
  parseWorkspaceStateMeta,
  type WorkspaceStateLead,
} from '@/lib/workspace-state-meta';
import { WorkspaceStateView } from './WorkspaceStateView';
import { OnboardingModal } from './OnboardingModal';
import { TaskSetupModal } from './TaskSetupModal';
import { ChatEmptyState } from './ChatEmptyState';

interface ChatSurfaceProps {
  agents: Agent[];
  tasks: Task[];
  dataLoading: boolean;
  /** Additional plus-menu actions from the page. ChatSurface prepends its own built-in actions. */
  plusMenuActions?: PlusMenuAction[];
  onContextSubmit: (message: string) => void;
}

export function ChatSurface({
  agents,
  tasks,
  dataLoading,
  plusMenuActions = [],
  onContextSubmit,
}: ChatSurfaceProps) {
  const { messages, sendMessage } = useTP();

  // --- Overview modal state ---
  const [overviewOpen, setOverviewOpen] = useState(false);
  const [overviewLead, setOverviewLead] = useState<WorkspaceStateLead | null>(null);
  const [overviewReason, setOverviewReason] = useState<string | null>(null);

  // --- Onboarding modal state ---
  const [onboardingOpen, setOnboardingOpen] = useState(false);

  // --- Task setup modal state ---
  const [taskSetupOpen, setTaskSetupOpen] = useState(false);
  const [taskSetupInitialNotes, setTaskSetupInitialNotes] = useState('');

  // --- Empty-state chip seed (ADR-190) ---
  // When a chip is clicked in ChatEmptyState, this seeds the composer input
  // via ChatPanel's draftSeed prop. Each click gets a unique id so the same
  // chip can be clicked twice in a row and still re-seed.
  const [chipSeed, setChipSeed] = useState<{ id: string; text: string } | null>(null);
  const handleChipClick = useCallback((text: string) => {
    setChipSeed({ id: `chip-${Date.now()}`, text });
  }, []);

  // Track the last message id we processed for marker directives.
  const [lastProcessedId, setLastProcessedId] = useState<string | null>(null);

  // Watch the latest assistant message for the workspace-state marker.
  // ADR-190: onboarding marker auto-trigger retired. OnboardingModal is now
  // opened only via the plus-menu "Update workspace" action. Onboarding is
  // conversational (prompt guidance in yarnnn_prompts/onboarding.py).
  useEffect(() => {
    if (messages.length === 0) return;
    const latest = messages[messages.length - 1];
    if (latest.role !== 'assistant') return;
    if (latest.id === lastProcessedId) return;
    if (!latest.content) return;

    setLastProcessedId(latest.id);

    const { directive } = parseWorkspaceStateMeta(latest.content);
    if (directive) {
      setOnboardingOpen(false);
      setOverviewOpen(true);
      setOverviewLead(directive.lead);
      setOverviewReason(directive.reason ?? null);
    }
  }, [messages, lastProcessedId]);

  // Manual Overview toggle — opens if closed, closes if open.
  const handleOverviewToggle = useCallback(() => {
    setOverviewOpen((prev) => {
      if (prev) return false;
      // Manual open: default tab, no TP call.
      setOnboardingOpen(false);
      setOverviewLead(null); // null tells WorkspaceStateView to default to 'overview'
      setOverviewReason(null);
      return true;
    });
  }, []);

  const handleOverviewClose = useCallback(() => setOverviewOpen(false), []);
  const handleOnboardingClose = useCallback(() => setOnboardingOpen(false), []);

  // "Ask TP" from Overview modal flags tab — sends prompt and closes modal.
  const handleAskTP = useCallback(
    (prompt: string) => {
      setOverviewOpen(false);
      sendMessage(prompt);
    },
    [sendMessage],
  );

  // "Open Onboarding" from Overview modal flags tab (identity-empty card).
  const handleOpenOnboarding = useCallback(() => {
    setOverviewOpen(false);
    setOnboardingOpen(true);
  }, []);

  // Onboarding form submit — sends composed message to TP and closes modal.
  const handleOnboardingSubmit = useCallback(
    (msg: string) => {
      setOnboardingOpen(false);
      onContextSubmit(msg);
    },
    [onContextSubmit],
  );

  // Task setup modal — opened from plus-menu or Heads Up idle-agents flag.
  const handleOpenTaskSetup = useCallback((initialNotes = '') => {
    setOverviewOpen(false);
    setOnboardingOpen(false);
    setTaskSetupInitialNotes(initialNotes);
    setTaskSetupOpen(true);
  }, []);

  const handleTaskSetupClose = useCallback(() => setTaskSetupOpen(false), []);

  const handleTaskSetupSubmit = useCallback(
    (msg: string) => {
      setTaskSetupOpen(false);
      sendMessage(msg);
    },
    [sendMessage],
  );

  // Built-in plus-menu actions — prepended to any page-supplied actions.
  const allPlusMenuActions = useMemo<PlusMenuAction[]>(() => [
    {
      id: 'create-task',
      label: 'Start new work',
      icon: ListChecks,
      verb: 'show',
      onSelect: () => handleOpenTaskSetup(),
    },
    {
      id: 'update-context',
      label: 'Update workspace',
      icon: SlidersHorizontal,
      verb: 'show',
      onSelect: () => handleOpenOnboarding(),
    },
    ...plusMenuActions,
  ], [plusMenuActions, handleOpenTaskSetup, handleOpenOnboarding]);

  // Overview toggle button — lives in the surface header.
  const overviewAction = (
    <button
      type="button"
      onClick={handleOverviewToggle}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      title="Open workspace"
    >
      <LayoutDashboard className="w-3.5 h-3.5" />
      Workspace
    </button>
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
          actions={overviewAction}
        />
      </div>
      <div className="flex-1 min-h-0">
        <div className="mx-auto h-full w-full max-w-3xl px-3 sm:px-4 py-3 sm:py-5">
          <ChatPanel
            surfaceOverride={{ type: 'chat' }}
            plusMenuActions={allPlusMenuActions}
            placeholder="Type, drop a file, or paste a link..."
            showCommandPicker={true}
            showInputDivider={false}
            draftSeed={chipSeed}
            emptyState={(helpers) => (
              <ChatEmptyState
                onChipClick={handleChipClick}
                onUploadClick={helpers.requestUpload}
              />
            )}
          />
        </div>
      </div>

      {/* Overview modal — read-only diagnostic dashboard */}
      <WorkspaceStateView
        open={overviewOpen}
        lead={overviewLead}
        agents={agents}
        tasks={tasks}
        dataLoading={dataLoading}
        reason={overviewReason}
        onClose={handleOverviewClose}
        onAskTP={handleAskTP}
        onOpenOnboarding={handleOpenOnboarding}
        onOpenTaskSetup={handleOpenTaskSetup}
      />

      {/* Onboarding modal — first-run identity capture */}
      <OnboardingModal
        open={onboardingOpen}
        onClose={handleOnboardingClose}
        onSubmit={handleOnboardingSubmit}
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
