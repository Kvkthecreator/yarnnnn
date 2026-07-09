'use client';

/**
 * FreddieAboutPanel — who Freddie is (the About pane of the Freddie System
 * Agent door). ADR-426 amendment (2026-07-09).
 *
 * Replaces the retired Capabilities pane. Capabilities read
 * /workspace/operation/specs/ ("the Reviewer's capability library" — quality
 * contracts for producing recurring outputs), a pre-ADR-414 concept: post
 * ADR-414 the specs library is a HIRED agent's operation concern, not the
 * system agent's, and the pane invited the operator to configure output specs
 * for the steward — which the steward does not produce.
 *
 * This pane answers the honest first question a new operator has when they open
 * the door: "What IS Freddie, and what can I do here?" It is read-only prose —
 * Freddie's persona is a KERNEL CONSTANT (ADR-414 D2), not operator-authored, so
 * there is nothing to fetch or edit. The explanatory text mirrors the canonical
 * steward identity (api/services/orchestration.py::DEFAULT_STEWARD_IDENTITY_MD);
 * it is stable, so it lives FE-side rather than behind a new endpoint.
 *
 * The key thing the operator should take away: you TUNE Freddie (Autonomy =
 * how far it acts without asking, Budget = its spend envelope) — you do not
 * author its character. That distinction is what the whole ADR-414 steward model
 * makes true, and it is why this pane exists instead of a config surface.
 */

import { PaneHeader } from '@/components/settings/SettingsPaneShell';
import { FreddieAvatar } from '@/components/freddie/FreddieAvatar';
import { ShieldCheck, Wallet, Activity as ActivityIcon, Lock } from 'lucide-react';

export function FreddieAboutPanel() {
  return (
    <div>
      <PaneHeader
        icon={ShieldCheck}
        title="About Freddie"
        subtitle="Your workspace's system agent — the substrate steward."
        bordered={false}
      />

      {/* Identity card — the mascot + who Freddie is */}
      <div className="mb-6 flex items-start gap-4 rounded-lg border border-border p-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-muted">
          <FreddieAvatar animate={false} className="h-9 w-9" />
        </div>
        <div className="min-w-0 space-y-2 text-sm text-muted-foreground">
          <p>
            <span className="font-medium text-foreground">Freddie</span> is this
            workspace&rsquo;s installed system agent — its substrate steward. It keeps
            your workspace coherent on your behalf while you&rsquo;re away: placing what
            comes in, attributing every change honestly, reconciling conflict between
            the people and AIs who share the workspace, and surfacing what it
            can&rsquo;t resolve.
          </p>
          <p>
            It reasons from what the substrate shows — not from memory or assumption.
            When something is missing, it says so plainly rather than inventing it.
            Freddie is careful, literal, and quietly thorough: the operator&rsquo;s hands
            and memory inside the system. The work is the substrate, not the agent.
          </p>
        </div>
      </div>

      {/* What Freddie does NOT do — the boundary that makes tuning meaningful */}
      <div className="mb-6 rounded-lg border border-border p-4">
        <h3 className="mb-2 text-sm font-medium text-foreground">The boundary</h3>
        <p className="text-sm text-muted-foreground">
          Freddie takes no consequential external action on its own authority — it
          moves no money and sends no irreversible message. That kind of judgment
          belongs to purpose-built agents you hire for an operation, never to the
          steward. A workspace with just Freddie is complete, not unfinished — it
          simply runs no operation yet.
        </p>
      </div>

      {/* You tune, you don't author — the ADR-414 point, made concrete */}
      <div className="rounded-lg border border-border p-4">
        <h3 className="mb-3 text-sm font-medium text-foreground">
          What you configure here
        </h3>
        <p className="mb-4 text-sm text-muted-foreground">
          You <span className="font-medium text-foreground">tune</span> Freddie — you
          don&rsquo;t author its character. Its reasoning is fixed; what you control is how
          far it&rsquo;s allowed to go and what it may spend.
        </p>
        <ul className="space-y-3 text-sm">
          <li className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="text-muted-foreground">
              <span className="font-medium text-foreground">Autonomy</span> — how much
              Freddie decides without asking first.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <Wallet className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="text-muted-foreground">
              <span className="font-medium text-foreground">Budget</span> — the spend
              envelope it works within.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <ActivityIcon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="text-muted-foreground">
              <span className="font-medium text-foreground">Activity</span> — what
              Freddie has actually done on your behalf.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <Lock className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="text-muted-foreground">
              Freddie&rsquo;s <span className="font-medium text-foreground">character</span>{' '}
              is built in and not editable — a program you activate replaces it with
              the operation&rsquo;s own agent.
            </span>
          </li>
        </ul>
      </div>
    </div>
  );
}
