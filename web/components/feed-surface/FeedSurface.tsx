'use client';

/**
 * FeedSurface — operations timeline + Conversation drawer (ADR-289 Phase 2).
 *
 *   <SurfaceIdentityHeader actions={[Filter, Context, Talk]} />
 *   <FeedTimeline /> ........... operations timeline (invocation cards, etc.)
 *   <ConversationDrawer /> ..... chat-shaped exchange slide-over (closed by default)
 *   <WorkspaceContextOverlay /> (pure reads, zero LLM)
 *
 * Rewired by ADR-289 Phase 2: the legacy single-panel FeedPanel rendering
 * is split into a typed-event timeline (FeedTimeline) + a slide-over
 * Conversation surface (ConversationDrawer). Bubbles are scoped to the
 * Conversation surface only; the timeline uses typed event rows.
 *
 * Engagement model:
 *   - Operator opens the drawer to engage a conversation (composer lives
 *     inside the drawer). Clicking an OperatorEventMarker's "opened
 *     conversation →" affordance also opens the drawer.
 *   - Drawer close returns to full Feed view.
 *   - Autonomous wakes that fire while the drawer is open emit narrative
 *     rows; the FeedTimeline behind picks them up but the drawer stays
 *     focused on the addressed exchange. Per ADR-289 Phase 2 design
 *     lock-in (silent autonomous wakes during drawer).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { BookOpen, Filter, MessageCircle } from 'lucide-react';
import { FeedTimeline } from '@/components/feed/FeedTimeline';
import { ConversationDrawer } from '@/components/feed/ConversationDrawer';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { useNarrative } from '@/contexts/NarrativeContext';
import {
  parseSnapshotMeta,
  type SnapshotLead,
} from '@/lib/content-shapes/snapshot';
import { WorkspaceContextOverlay } from './WorkspaceContextOverlay';
import { AutonomyHeaderChip } from './AutonomyHeaderChip';
import { FeedEmptyState } from './FeedEmptyState';
import { FeedFilterBar, parseChatFilterFromSearch } from './FeedFilterBar';
import { useReviewerPersona } from '@/lib/reviewer-persona';
import { cn } from '@/lib/utils';

interface FeedSurfaceProps {
  /** Additional plus-menu actions from the page. FeedSurface prepends its own built-in actions. */
  plusMenuActions?: PlusMenuAction[];
}

export function FeedSurface({
  plusMenuActions = [],
}: FeedSurfaceProps) {
  const { messages, sendMessage } = useNarrative();
  const searchParams = useSearchParams();
  const personaName = useReviewerPersona();

  // --- Context overlay state ---
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotLead, setSnapshotLead] = useState<SnapshotLead | null>(null);
  const [snapshotReason, setSnapshotReason] = useState<string | null>(null);

  // --- Conversation drawer state (ADR-289 Phase 2) ---
  const [drawerOpen, setDrawerOpen] = useState(false);
  const handleOpenDrawer = useCallback(() => setDrawerOpen(true), []);
  const handleCloseDrawer = useCallback(() => setDrawerOpen(false), []);
  // Open drawer scrolled to a specific invocation (called by an
  // OperatorEventMarker's "opened conversation →" affordance). The
  // ConversationPanel inside the drawer renders all addressed rows in
  // the workspace session — scrolling within is a Phase 2.1 refinement.
  const handleOpenConversation = useCallback((_invocationId: string) => {
    setDrawerOpen(true);
  }, []);

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
  // ADR-289 Phase 2: chips on FeedEmptyState now open the drawer.
  // Composer-prefill is a drawer-side concern.
  const handleChipClick = useCallback((_text: string) => {
    setDrawerOpen(true);
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

  // "Run this on a schedule" — seeds chat with a scheduling intent.
  // All mutation flows through Chat; no modal.
  const handleMakeRecurring = useCallback(
    (messageContent: string) => {
      const trimmed = messageContent.trim();
      const excerpt = trimmed.length > 280 ? trimmed.slice(0, 280) + '…' : trimmed;
      sendMessage(
        `Run this on a schedule — turn the output above into a recurrence. Quoted excerpt: "${excerpt}"`,
      );
    },
    [sendMessage],
  );

  // Plus-menu: pass through any page-supplied actions. No built-in modal
  // launcher — "Start new work" is handled by seeding the composer via
  // FeedEmptyState chips or just talking to YARNNN.
  const allPlusMenuActions = useMemo<PlusMenuAction[]>(
    () => [...plusMenuActions],
    [plusMenuActions],
  );

  // Context overlay toggle — replaces "Snapshot" button.
  // Label updated to "Context" — more honest about what it shows
  // (workspace substrate files), less jargony than "Snapshot".
  const snapshotAction = (
    <button
      type="button"
      onClick={handleSnapshotToggle}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      title="Open workspace context"
    >
      <BookOpen className="w-3.5 h-3.5" />
      Context
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

  // ADR-289 Phase 2: "Talk" button opens the Conversation drawer.
  // The Feed surface is the operations timeline; engaging a conversation
  // happens through the drawer (composer lives inside).
  const talkAction = (
    <button
      type="button"
      onClick={handleOpenDrawer}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-primary/40 bg-primary/5 text-primary hover:bg-primary/10 transition-colors"
      title={`Talk to ${personaName ?? 'Reviewer'}`}
    >
      <MessageCircle className="w-3.5 h-3.5" />
      Talk
    </button>
  );

  const headerActions = (
    <div className="flex items-center gap-1.5">
      {/* Commit G (2026-05-11): autonomy chip relocated from composer to
          feed header. Workspace-level posture belongs at the workspace
          frame, not the operator-input frame. Singular Implementation:
          one chip, one location — composer chip deleted in same commit. */}
      <AutonomyHeaderChip />
      {filterToggleAction}
      {snapshotAction}
      {talkAction}
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
          <FeedFilterBar />
        </div>
      )}
      <div className="flex-1 min-h-0">
        <div className="mx-auto h-full w-full max-w-3xl px-3 sm:px-4 py-3 sm:py-5">
          {/* ADR-289 Phase 2: FeedTimeline replaces FeedPanel on /feed.
              Renders typed-event rows (InvocationCard, OperatorEventMarker,
              StandaloneEventRow, DaySeparator) — no chat bubbles. The
              composer lives inside the ConversationDrawer; operator opens
              the drawer via the "Talk" header button or by clicking an
              existing OperatorEventMarker's "opened conversation →"
              affordance. */}
          <FeedTimeline
            onOpenConversation={handleOpenConversation}
            emptyState={
              <FeedEmptyState
                onChipClick={handleChipClick}
                onUploadClick={handleOpenDrawer}
              />
            }
          />
        </div>
      </div>

      {/* ADR-289 Phase 2: Conversation drawer (slide-over). Hosts the
          ConversationPanel scoped to `pulse='addressed'`. Composer lives
          inside. Autonomous wakes that fire while open remain silent in
          the drawer — they surface in the FeedTimeline behind, visible
          when the drawer closes. */}
      <ConversationDrawer
        open={drawerOpen}
        onClose={handleCloseDrawer}
        plusMenuActions={allPlusMenuActions}
        onMakeRecurring={handleMakeRecurring}
      />

      {/* Context overlay — 3-section primer (Mandate · Rules · Pulse) per
          2026-05-14 refactor. The legacy `tasks` prop dropped — the Pulse
          section reads its own activity data via api.agents.reviewerActivity()
          and api.proposals.list(). */}
      <WorkspaceContextOverlay
        open={snapshotOpen}
        lead={snapshotLead}
        reason={snapshotReason}
        onClose={handleSnapshotClose}
        onAskTP={handleAskYARNNN}
      />
    </div>
  );
}
