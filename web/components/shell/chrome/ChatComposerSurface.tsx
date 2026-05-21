'use client';

/**
 * ChatComposerSurface — ADR-297 D11 chrome surface (region: bottom-fixed,
 * archetype: input).
 *
 * Phase B placeholder. Per ADR-297 D11 the chat composer is a kernel
 * Input surface that the shell mounts in every authenticated view —
 * every operator can chat with YARNNN from any surface, not just /feed.
 *
 * Phase C lifts the actual composer affordance out of ConversationPanel
 * (web/components/tp/ConversationPanel.tsx) into this surface, threading
 * the per-surface state (surfaceOverride, draftSeed, pendingActionConfig,
 * emptyState, narrativeFilter) through DeskContext rather than props.
 *
 * In Phase B this component renders nothing — the surface is declared
 * and registered, the compositor reserves the bottom-fixed region for
 * it, but no operator-visible composer mounts yet. /feed continues to
 * carry its inline ConversationPanel; atomic surfaces continue to use
 * ThreePanelLayout.conversation. The compositor seam is ready; Phase C
 * fills it.
 */

export function ChatComposerSurface() {
  // Phase B: declared-but-empty. Phase C wires the composer body.
  return null;
}
