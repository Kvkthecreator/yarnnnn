'use client';

/**
 * PrinciplesTab — Thinking Partner detail Principles tab.
 *
 * Lifted from web/components/agents/reviewer/PrinciplesPane.tsx by
 * ADR-241 D2. Refactored to use the SubstrateTab shared shape by
 * ADR-236 Round 5+ extension (2026-04-30) — same look-and-feel as the
 * other TP tabs (Identity / Mandate / Autonomy / Memory).
 *
 * The substrate (/workspace/review/principles.md) is unchanged — same
 * path, same operator-authored framing per ADR-194 v2 + ADR-215 R3.
 * What changed is the surface: principles.md is the **judgment
 * framework TP applies to verdicts**, not a separate Reviewer-agent
 * property.
 *
 * Edit path: chat-mediated per ADR-236 Cluster A + EditInChatButton's
 * post-Cluster A R3 supersession. The "Edit in chat" affordance seeds
 * a principle-specific prompt; YARNNN handles the WriteFile dispatch.
 */

import { Scale } from 'lucide-react';
import { SubstrateTab } from './SubstrateTab';

export function PrinciplesTab() {
  return (
    <SubstrateTab
      title="Principles"
      icon={Scale}
      tagline="The judgment framework TP applies to verdicts. Operator-authored; revision history preserved per ADR-209."
      path="/workspace/review/principles.md"
      editPrompt="I want to evolve my Reviewer's principles. Walk me through the current declaration and help me decide what to change."
      emptyStateBody={
        <>
          No principles declared yet. The Reviewer applies these to every proposal —
          declaring them sharpens what gets approved vs rejected.{' '}
          <strong>Use Edit in chat</strong> to author your first set with YARNNN.
        </>
      }
    />
  );
}
