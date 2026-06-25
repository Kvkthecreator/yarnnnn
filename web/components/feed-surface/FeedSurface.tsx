'use client';

/**
 * FeedSurface — operations timeline (ADR-289 Phase 2 + ADR-297 D16 + D18.2).
 *
 *   <SurfaceIdentityHeader actions={[Filter, Context]} />
 *   <FeedTimeline /> ........... operations timeline (invocation cards, etc.)
 *   <WorkspaceContextOverlay /> (pure reads, zero LLM)
 *
 * Pre-D16 /feed owned its own ConversationDrawer slide-over for
 * chat-shaped exchanges. ADR-297 D16 (2026-05-22) collapsed all chat
 * affordances into the universal ChatDrawerSurface mounted in shell
 * chrome. /feed's local drawer + useSuppressShellComposer call DELETED.
 *
 * D18.2 (2026-05-22 follow-up) deletes the in-header "Talk" button.
 * The universal FAB (Desktop.tsx D17) summons the drawer from any
 * surface, so a per-surface Talk button is redundant chrome —
 * Singular Implementation: one summon path, the FAB. Empty-state
 * chip clicks + OperatorEventMarker's "open conversation →"
 * affordance continue to route through useShellChrome().openDrawer().
 *
 * Engagement model (post-D18.2):
 *   - Operator clicks the FAB anywhere → drawer opens.
 *   - FeedTimeline shows typed event rows, no chat bubbles. Bubbles
 *     live in the drawer's ConversationPanel scoped to pulse='addressed'.
 *   - Autonomous wakes emit narrative rows; FeedTimeline picks them up.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { BookOpen, Filter } from 'lucide-react';
import { FeedTimeline } from '@/components/feed/FeedTimeline';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { useNarrative } from '@/contexts/NarrativeContext';
import {
  parseSnapshotMeta,
  type SnapshotLead,
} from '@/lib/content-shapes/snapshot';
import { WorkspaceContextOverlay } from './WorkspaceContextOverlay';
import { FeedEmptyState } from './FeedEmptyState';
import { FeedFilterBar, parseChatFilterFromSearch } from './FeedFilterBar';
import { useShellChrome } from '@/components/shell/ShellChromeContext';
import { cn } from '@/lib/utils';

// D16 (2026-05-22): FeedSurface no longer accepts external chat
// affordance props. Chat is the universal ChatDrawerSurface; FeedSurface
// is read-only (operations timeline). D18.2 (2026-05-22 follow-up):
// header Talk button deleted — the FAB is the singular summon path.
export function FeedSurface() {
  const { messages, sendMessage } = useNarrative();
  const searchParams = useSearchParams();

  // ADR-297 D16: universal drawer summon (replaces the pre-D16 local
  // drawerOpen state + ConversationDrawer mount). Every "open chat"
  // affordance on this surface now routes through ShellChromeContext.
  const { openDrawer } = useShellChrome();
  const handleOpenDrawer = useCallback(() => openDrawer(), [openDrawer]);
  // OperatorEventMarker's "open conversation →" affordance + empty-
  // state upload-chip click — same dispatch as the deleted Talk button.
  // Scroll-to-invocation deferred.
  const handleOpenConversation = useCallback(
    (_invocationId: string) => openDrawer(),
    [openDrawer],
  );

  // --- Context overlay state ---
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotLead, setSnapshotLead] = useState<SnapshotLead | null>(null);
  const [snapshotReason, setSnapshotReason] = useState<string | null>(null);

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

  // --- Empty-state chip seed (ADR-190 / ADR-297 D16) ---
  // Chips on FeedEmptyState summon the universal chat drawer.
  // Composer-prefill (the chip's `_text`) was a per-surface ad-hoc
  // affordance that D16 §5 deliberately dropped in favor of the
  // universal drawer — operator types their prompt from scratch.
  const handleChipClick = useCallback(
    (_text: string) => openDrawer(),
    [openDrawer],
  );

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

  // D16 (2026-05-22): "Run this on a schedule" affordance on
  // addressed messages temporarily off — see ADR-297 §D16 "does NOT
  // do" list. Operator can still graduate via direct chat.

  // Substrate overlay toggle — the Mandate/Rules/Pulse primer over the
  // workspace's substrate files. ADR-370 D5 renamed this "Context" → "Substrate":
  // the Feed now renders as the Flow lens INSIDE the Context boundary surface,
  // so a button labeled "Context" within one of Context's own lenses would
  // collide. "Substrate" is honest (it shows workspace substrate files) and
  // collision-free.
  const snapshotAction = (
    <button
      type="button"
      onClick={handleSnapshotToggle}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      title="Open workspace substrate"
    >
      <BookOpen className="w-3.5 h-3.5" />
      Substrate
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

  // ADR-297 D18.2 (2026-05-22): in-header Talk button DELETED. The
  // universal FAB summons the drawer from any surface; per-surface
  // Talk chrome is redundant. Singular Implementation: one summon path.

  const headerActions = (
    <div className="flex items-center gap-1.5">
      {/* ADR-297 D20 (2026-05-24): autonomy chip relocated from feed
          header to top-bar SystemStatusCluster. Workspace-level posture
          is kernel chrome, visible on every surface — Feed header is
          no longer special. AutonomyHeaderChip + PauseAutonomyModal
          deleted; pause/resume happens on /autonomy. */}
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
      {/* ADR-289 Phase 2a: header pinned at the top so the Talk button
          (and other actions) are always reachable. Pre-Phase-2a the
          header lived in the document scroll context — the FeedTimeline's
          auto-scroll-to-bottom meant operators couldn't reach the
          header without fighting the scroll. The header is now outside
          the scrolling container; FeedTimeline owns its own scroll. */}
      <div className="shrink-0 border-b border-border/40 bg-background z-10">
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
      </div>
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

      {/* ADR-297 D16: pre-D16 the per-/feed ConversationDrawer mounted
          here. Now the chat affordance lives in shell chrome
          (ChatDrawerSurface — bottom-center FAB + universal slide-over
          drawer). The Talk button + chip clicks + open-conversation
          marker links all summon that universal drawer via
          useShellChrome().openDrawer(). */}

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
