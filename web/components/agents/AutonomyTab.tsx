'use client';

/**
 * AutonomyTab — Reviewer detail Autonomy tab (ADR-251).
 *
 * Renders /workspace/context/_shared/AUTONOMY.md per ADR-217. The
 * autonomy substrate is the operator's delegation ceiling to the Reviewer
 * seat — manual / assisted / bounded_autonomous / autonomous, with optional
 * per-domain overrides + ceiling_cents.
 *
 * Moved from System Agent surface to Reviewer surface by ADR-251 D4.
 * Autonomy is the Reviewer's operating mandate, not the system's config.
 *
 * The chat composer's autonomy chip (ADR-238) reads the same file
 * and links here for the operator to see the full posture.
 */

import { ShieldCheck } from 'lucide-react';
import { SubstrateTab } from './SubstrateTab';

export function AutonomyTab() {
  return (
    <SubstrateTab
      title="Autonomy"
      icon={ShieldCheck}
      tagline="Your delegation ceiling to the Reviewer — how much the Reviewer can execute on your behalf. Per ADR-217: manual / assisted / bounded_autonomous / autonomous."
      path="/workspace/context/_shared/AUTONOMY.md"
      editPrompt="Help me revise my Reviewer's autonomy delegation. Show me the current declaration and walk me through what I'd change — default level, ceilings, per-domain overrides."
      emptyBody={
        <>
          Autonomy declares how much the Reviewer can decide on your behalf. Default at signup
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
