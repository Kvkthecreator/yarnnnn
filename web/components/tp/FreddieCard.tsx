'use client';

/**
 * FreddieCard — renders Reviewer narrative entries as chat bubbles.
 *
 * ADR-258: three participants, one bubble shape. The Reviewer is a
 * conversational participant — differentiated by label (persona name)
 * and position, not by color. Semantic state (approved/rejected/deferred)
 * appears as a compact inline chip, not as bubble background tinting.
 *
 * Verdict types:
 *   observation          → dim collapsed one-liner (housekeeping)
 *   addressed / heartbeat → plain muted bubble, no verdict chip
 *   approve / reject / defer → muted bubble + inline status chip
 */

import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { CheckCircle2, XCircle, PauseCircle, Eye, Zap, Loader2 } from 'lucide-react';
import { FreddieAvatar } from '@/components/freddie/FreddieAvatar';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { FreddieCardData } from '@/types/desk';
import { cn } from '@/lib/utils';

interface FreddieCardProps {
  data: FreddieCardData;
  content: string;
  personaName?: string | null;
  /** Confidence from the addressed-mode assessment ('low' | 'medium' | 'high') */
  confidence?: string | null;
  /** Directive dispatched by System Agent after Reviewer assessment, if any */
  directiveDispatched?: string | null;
  /** ADR-399: the turn artifact — reasoning + calls, in order, persistent. */
  process?: FreddieProcessItem[];
}

export type FreddieProcessItem =
  | { kind: 'thinking'; text: string }
  | {
      kind: 'tool';
      name: string;
      detail: string;
      status: 'pending' | 'success' | 'failed';
      result: string;
    };

/** The turn's process, rendered the way the market's chat grammar taught
 *  everyone to read it: reasoning as dim collapsible disclosures, tool calls
 *  as compact rows — in the order they happened, never removed (ADR-399:
 *  append-only within one narrative entry). Content is what the runtime
 *  REPORTED, never an FE-invented label (the ADR-351 D4 line, kept). */
function ProcessTrail({ items }: { items: FreddieProcessItem[] }) {
  return (
    <div className="mt-1.5 mb-1 space-y-0.5">
      {items.map((item, i) =>
        item.kind === 'thinking' ? (
          <details key={i} className="group text-[10px] text-muted-foreground/45">
            <summary className="cursor-pointer list-none select-none italic hover:text-muted-foreground/70">
              <span className="group-open:hidden">▸ reasoning…</span>
              <span className="hidden group-open:inline">▾ reasoning</span>
            </summary>
            <p className="mt-0.5 pl-3 whitespace-pre-wrap italic leading-snug">{item.text}</p>
          </details>
        ) : (
          <div
            key={i}
            className="flex items-baseline gap-1.5 text-[10px] font-mono text-muted-foreground/50 leading-tight"
          >
            {item.status === 'pending' ? (
              <Loader2 className="w-2.5 h-2.5 animate-spin shrink-0 self-center" />
            ) : item.status === 'failed' ? (
              <XCircle className="w-2.5 h-2.5 shrink-0 self-center text-red-500/60" />
            ) : (
              <CheckCircle2 className="w-2.5 h-2.5 shrink-0 self-center text-muted-foreground/40" />
            )}
            <span className="shrink-0">{item.name}</span>
            {item.detail && <span className="truncate text-muted-foreground/40">{item.detail}</span>}
            {item.result && item.status !== 'pending' && (
              <span className="truncate text-muted-foreground/35">→ {item.result}</span>
            )}
          </div>
        )
      )}
    </div>
  );
}

function occupantLabel(occupant: string | undefined, personaName?: string | null): string {
  if (!occupant) return personaName ?? 'Freddie';
  if (occupant.startsWith('human:')) return 'You';
  if (occupant.startsWith('ai:')) return personaName ?? 'Freddie';
  if (occupant === 'reviewer-layer:observed') return 'Freddie';
  return personaName ?? occupant;
}

function VerdictChip({ verdict }: { verdict: string }) {
  if (verdict === 'approve') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-700 dark:text-emerald-400">
        <CheckCircle2 className="w-3 h-3" />
        Approved
      </span>
    );
  }
  if (verdict === 'reject') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground/70">
        <XCircle className="w-3 h-3" />
        Rejected
      </span>
    );
  }
  if (verdict === 'defer') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground/70">
        <PauseCircle className="w-3 h-3" />
        Deferred
      </span>
    );
  }
  return null;
}

export function FreddieCard({ data, content, personaName, confidence, directiveDispatched, process }: FreddieCardProps) {
  const { verdict, occupant, actionType, proposalId } = data;
  const persona = occupantLabel(occupant, personaName);

  const isObservation = verdict === 'observation' || occupant === 'reviewer-layer:observed';
  const isAddressed = verdict === 'addressed' || verdict === 'heartbeat';
  const isProposalVerdict = verdict === 'approve' || verdict === 'reject' || verdict === 'defer';

  // Observations: dim one-liner — housekeeping weight
  if (isObservation) {
    return (
      <div className="flex items-center gap-1.5 px-1 py-0.5 my-0.5 opacity-35">
        <Eye className="w-3 h-3 text-muted-foreground shrink-0" />
        <span className="text-[10px] text-muted-foreground">
          {persona} observed{actionType ? ` · ${actionType}` : ''}
        </span>
      </div>
    );
  }

  // All non-observation entries: uniform muted bubble — same shape as System Agent
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-muted rounded-bl-md">
      {/* Label row: Freddie's face + persona name + verdict chip. The mascot
          (2026-07-01) gives every Freddie message the same identity the chat
          header + top-bar chip carry — one recognizable actor. Static here (a
          settled message, not a live reply). */}
      <div className="flex items-center gap-1.5 mb-1">
        <FreddieAvatar animate={false} className="w-3.5 h-3.5" />
        <span className="text-[9px] font-medium text-muted-foreground/50 tracking-wider uppercase">
          {persona}
        </span>
        {isProposalVerdict && <VerdictChip verdict={verdict!} />}
        {isProposalVerdict && actionType && (
          <span className="text-[10px] font-mono text-muted-foreground/40">{actionType}</span>
        )}
      </div>

      {/* ADR-399: the turn artifact — process trail (live + settled) */}
      {process && process.length > 0 && <ProcessTrail items={process} />}

      {/* Content — ADR-398 D3: substrate paths + proposal ids render as
          SurfaceLinks (OS-owned linkification; the model never authors URLs) */}
      {content && <MarkdownRenderer content={content} compact linkifySubstrate />}

      {/* Status chrome — directive dispatched + confidence (addressed mode) */}
      {(directiveDispatched || (isAddressed && confidence && confidence !== 'high')) && (
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          {directiveDispatched && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground/50">
              <Zap className="w-2.5 h-2.5" />
              {directiveDispatched}
            </span>
          )}
          {isAddressed && confidence === 'low' && (
            <span className="text-[10px] text-muted-foreground/40">low confidence</span>
          )}
          {isAddressed && confidence === 'medium' && (
            <span className="text-[10px] text-muted-foreground/40">medium confidence</span>
          )}
        </div>
      )}

      {/* Audit trail link for proposal verdicts. Routes to the raw
          decisions.md substrate file via the Context surface (the L1
          Universal Raw View per ADR-245). The previously-promised
          /work?tab=decisions surface (ADR-241 D3) was never built;
          retargeted to the working substrate read 2026-05-11. */}
      {proposalId && isProposalVerdict && (
        <SurfaceLink
          to="files"
          params={{ path: '/workspace/persona/judgment_log.md' }}
          className="text-[10px] text-muted-foreground/40 hover:text-foreground transition-colors mt-1 block"
        >
          Audit trail →
        </SurfaceLink>
      )}
    </div>
  );
}
