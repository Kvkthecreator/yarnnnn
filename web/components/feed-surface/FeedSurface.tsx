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
 * Singular Implementation: one summon path, the FAB.
 *
 * Engagement model (post-D18.2):
 *   - Operator clicks the FAB anywhere → drawer opens.
 *   - FeedTimeline shows typed event rows, no chat bubbles. Bubbles
 *     live in the drawer's ConversationPanel scoped to pulse='addressed'.
 *   - Autonomous wakes emit narrative rows; FeedTimeline picks them up.
 */

import { useCallback, useEffect, useState } from 'react';
import { BookOpen } from 'lucide-react';
import { FeedTimeline } from '@/components/feed/FeedTimeline';
import { useNarrative } from '@/contexts/NarrativeContext';
import {
  parseSnapshotMeta,
  type SnapshotLead,
} from '@/lib/content-shapes/snapshot';
import { WorkspaceContextOverlay } from './WorkspaceContextOverlay';

// D16 (2026-05-22): FeedSurface no longer accepts external chat
// affordance props. Chat is the universal ChatDrawerSurface; FeedSurface
// is read-only (operations timeline). D18.2 (2026-05-22 follow-up):
// header Talk button deleted — the FAB is the singular summon path.
//
// 2026-07-07 prune: the sole remaining mount is Channels → In (ADR-385 /
// ADR-404 — the Flow pane retired, Notifications Activity re-mounted on
// the timeline ledger). The filter bar (weight/identity/task chips that
// no longer filtered anything), the FeedEmptyState chat-summon path, and
// the OperatorEventMarker open-conversation affordance were unreachable
// under the inbound filter and are deleted.
interface FeedSurfaceProps {
  messageFilter?: (m: import('@/types/desk').TPMessage) => boolean;
  emptyLabel?: string;
}

export function FeedSurface({ messageFilter, emptyLabel }: FeedSurfaceProps = {}) {
  const { messages, sendMessage } = useNarrative();

  // --- Context overlay state ---
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotLead, setSnapshotLead] = useState<SnapshotLead | null>(null);
  const [snapshotReason, setSnapshotReason] = useState<string | null>(null);

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

  // ADR-297 D18.2 (2026-05-22): in-header Talk button DELETED. The
  // universal FAB summons the drawer from any surface; per-surface
  // Talk chrome is redundant. Singular Implementation: one summon path.

  const headerActions = (
    <div className="flex items-center gap-1.5">
      {/* ADR-297 D20 (2026-05-24): autonomy chip left the feed header.
          (It later lived on the top-bar status cluster, itself retired
          2026-07-08.) AutonomyHeaderChip + PauseAutonomyModal deleted;
          pause/resume happens on Workspace Settings → Autonomy. */}
      {snapshotAction}
    </div>
  );

  return (
    <div className="flex h-full flex-col bg-background">
      {/* ADR-289 Phase 2a: header pinned at the top so the actions (filter,
          substrate) are always reachable. ADR-377 (2026-06-26): the redundant
          in-pane `yarnnn` brand mark + title is REMOVED — the Flow pane lives
          inside Context (the global locator already names it; the OS shell
          owns identity). Only the functional actions row remains.

          2026-06-30: the `mx-auto` was dropped from the header/filter/body
          (kept `max-w-3xl` for line length). FeedSurface mounts in fullBleed
          (=fill) panes (Channels Flow/In, Notifications Activity); `mx-auto`
          floated the timeline dead-center in a maximized window, leaving a
          large gap between the split-nav and the rows. Left-pinned now —
          matching the SettingsPaneShell `reading` width policy. */}
      <div className="shrink-0 border-b border-border/40 bg-background z-10">
        <div className="w-full max-w-3xl px-3 sm:px-4">
          <div className="flex items-center justify-end gap-2 py-2">
            {headerActions}
          </div>
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <div className="h-full w-full max-w-3xl px-3 sm:px-4 py-3 sm:py-5">
          {/* ADR-289 Phase 2: FeedTimeline renders typed-event rows
              (InvocationCard, OperatorEventMarker, StandaloneEventRow,
              DaySeparator) — no chat bubbles. */}
          <FeedTimeline
            messageFilter={messageFilter}
            emptyState={
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <p className="text-sm font-medium text-foreground">
                  {emptyLabel ?? 'Nothing here yet.'}
                </p>
              </div>
            }
          />
        </div>
      </div>

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
