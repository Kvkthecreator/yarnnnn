'use client';

/**
 * ChatSurface — YARNNN chat surface.
 *
 *   <SurfaceIdentityHeader actions={[Filter, Context]} />
 *   <ChatPanel emptyState={<ChatEmptyState />} />
 *   <WorkspaceContextOverlay /> (pure reads, zero LLM)
 *
 * All mutations go through Chat. No separate creation modals.
 * RecurrenceSetupModal removed — "Start new work" seeds the composer;
 * YARNNN handles intent conversationally.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { BookOpen, Filter } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import type { Recurrence } from '@/types';
import { useTP } from '@/contexts/TPContext';
import {
  parseSnapshotMeta,
  type SnapshotLead,
} from '@/lib/content-shapes/snapshot';
import { WorkspaceContextOverlay } from './WorkspaceContextOverlay';
// RecurrenceSetupModal removed — "Start new work" seeds the composer.
import { ChatEmptyState } from './ChatEmptyState';
import { ChatFilterBar, parseChatFilterFromSearch } from './ChatFilterBar';
import { cn } from '@/lib/utils';

interface ChatSurfaceProps {
  /** Tasks feed the Snapshot overlay's Recent tab (last-run list). */
  tasks: Recurrence[];
  /** Additional plus-menu actions from the page. ChatSurface prepends its own built-in actions. */
  plusMenuActions?: PlusMenuAction[];
}

export function ChatSurface({
  tasks,
  plusMenuActions = [],
}: ChatSurfaceProps) {
  const { messages, sendMessage } = useTP();
  const searchParams = useSearchParams();

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
  // ChatEmptyState chips or just talking to YARNNN.
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

      {/* Context overlay — replaces SnapshotModal. WorkspaceFileView renders
          substrate files inline; no tabs, one scrollable panel. */}
      <WorkspaceContextOverlay
        open={snapshotOpen}
        lead={snapshotLead}
        reason={snapshotReason}
        tasks={tasks}
        onClose={handleSnapshotClose}
        onAskTP={handleAskYARNNN}
      />

      {/* RecurrenceSetupModal removed — all creation via Chat */}
    </div>
  );
}
