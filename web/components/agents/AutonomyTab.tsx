'use client';

/**
 * AutonomyTab — Thinking Partner detail Autonomy tab.
 *
 * Renders /workspace/context/_shared/AUTONOMY.md per ADR-217. The
 * autonomy substrate is the operator's standing intent about how
 * much judgment authority TP carries on their behalf — manual /
 * assisted / bounded_autonomous / autonomous, with optional per-domain
 * overrides + ceiling_cents.
 *
 * The chat composer's autonomy chip (ADR-238) reads the same file
 * and links here for the operator to see the full posture (per
 * ADR-236 Cluster B). This tab is that destination.
 *
 * Authored 2026-04-30 by ADR-236 Round 5+ extension.
 */

import { ShieldCheck } from 'lucide-react';
import { SubstrateTab } from './SubstrateTab';

export function AutonomyTab() {
  return (
    <SubstrateTab
      title="Autonomy"
      icon={ShieldCheck}
      tagline="How much judgment authority TP carries on your behalf. Single source of truth for delegation per ADR-217 — manual / assisted / bounded_autonomous / autonomous."
      path="/workspace/context/_shared/AUTONOMY.md"
      editPrompt="Help me revise my autonomy delegation. Show me the current declaration and walk me through what I'd change — default level, ceilings, per-domain overrides."
      emptyStateBody={
        <>
          Autonomy declares how much TP can decide on your behalf. Default at signup
          is <code className="rounded bg-muted px-1 py-0.5 text-[11px]">manual</code> —
          every action waits for your explicit approval. Widen via{' '}
          <code className="rounded bg-muted px-1 py-0.5 text-[11px]">assisted</code>,{' '}
          <code className="rounded bg-muted px-1 py-0.5 text-[11px]">bounded_autonomous</code>,
          or <code className="rounded bg-muted px-1 py-0.5 text-[11px]">autonomous</code>{' '}
          as confidence in the operation grows. <strong>Use Edit in chat</strong> to
          author your delegation.
        </>
      }
    />
  );
}
