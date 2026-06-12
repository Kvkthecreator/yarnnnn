'use client';

/**
 * AutonomyCard — L3 component for /workspace/governance/_autonomy.yaml.
 *
 * Renamed from DelegationCard (2026-05-24) to align with the substrate file
 * (_autonomy.yaml) and the operator's mental model. The schema field
 * `default_delegation` stays — it's the precise data-layer term for the
 * delegated level. At the operator surface the broader concept is Autonomy.
 *
 * The only concept component with a Direct mutation — `setLevel()` writes
 * the file without going through chat (it's a discrete config value,
 * not authored prose). Per the 2026-05-24 design polish: the full variant
 * gates every mutation behind a confirm modal because switching autonomy
 * level has capital impact and one-click commits were too easy to trigger
 * accidentally.
 *
 * Variants:
 *   full    — /autonomy page (four-option control + description + confirm modal)
 *   compact — context overlay (current level + one-line description)
 *   chip    — chat composer (level badge only, read-only)
 *
 * See docs/design/WORKSPACE-COMPONENTS.md §2.
 */

import { useEffect, useState } from 'react';
import { ShieldCheck, ArrowRight, Lock, Plus, X } from 'lucide-react';
import { useAutonomy, type AutonomyLevel } from '@/lib/content-shapes/autonomy';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { WorkspaceRevisionSummary } from '@/types';
import { RevisionFootnote } from './RevisionFootnote';
import { ConfirmDialChange } from './ConfirmDialChange';

export type AutonomyVariant = 'full' | 'compact' | 'chip';

interface AutonomyCardProps {
  variant?: AutonomyVariant;
  /** For chip variant: click opens /autonomy */
  onOpen?: () => void;
  /** ADR-266 D8: pre-fetched _autonomy.yaml content (from setup-bundle).
   *  When supplied, useAutonomy primes from this and skips its self-fetch. */
  initialContent?: string | null;
  /** ADR-266 D7: most-recent revision metadata for the footnote line. */
  lastRevision?: WorkspaceRevisionSummary | null;
  className?: string;
}

// Commit F (2026-05-11): canonical 3-value enum, matches backend
// _VALID_DELEGATION_LEVELS in api/services/review_policy.py.
// `assisted` was retired — it had no backend semantics distinct from
// `manual` and was silently treated as manual by should_auto_execute_verdict.
// `bounded_autonomous` collapsed to `bounded` (Singular Implementation).
//
// `consequence` is the one-line operator-facing summary surfaced by the
// confirm modal on switch attempts (2026-05-24 design polish). Phrased in
// terms of what changes about the Reviewer's authority, not what the dial
// "means."
const LEVELS: {
  value: AutonomyLevel;
  label: string;
  description: string;
  consequence: string;
}[] = [
  {
    value: 'manual',
    label: 'Manual',
    description: 'Every action waits for your approval before executing.',
    consequence: 'Every Reviewer action will pause for your approval. You become the bottleneck on every decision.',
  },
  {
    value: 'bounded',
    label: 'Bounded',
    // ADR-338 D4.2: surface the schema-inert reality. `bounded` applies the
    // ceiling to capital actions only; substrate writes (file edits) queue
    // under BOTH manual and bounded — only `autonomous` auto-applies them.
    description: 'Capital actions auto-execute within your ceiling. Substrate edits still queue for approval.',
    consequence: 'The Reviewer will auto-execute capital actions within your declared ceiling. Substrate writes (file edits) STILL wait for your approval — only Autonomous auto-applies those. Higher-impact capital actions also wait.',
  },
  {
    value: 'autonomous',
    label: 'Autonomous',
    description: 'Full delegation within declared boundaries. You review outcomes.',
    consequence: 'The Reviewer will auto-execute every action — capital AND substrate edits — up to the ceiling without first checking in. You review outcomes after the fact.',
  },
];

export function AutonomyCard({
  variant = 'full',
  onOpen,
  initialContent,
  lastRevision,
  className,
}: AutonomyCardProps) {
  const { meta, loading, effectiveLevel, summary, setLevel, setNeverAuto } = useAutonomy({ initialContent });

  // Confirm-modal state (full variant only — compact + chip never mutate).
  const [pendingLevel, setPendingLevel] = useState<AutonomyLevel | null>(null);

  // ADR-340 P4 F2 — live consequence preview (the Night-Shift pattern).
  // The static per-level consequence copy tells the rule; this tells the
  // operator what the switch does to THEIR workspace RIGHT NOW, derived
  // from the live pending queue (no new state — pure derivation, the
  // same discipline as the AttentionCenter). Full variant only.
  const [pendingCounts, setPendingCounts] = useState<{ capital: number; total: number } | null>(null);
  useEffect(() => {
    if (variant !== 'full') return;
    let cancelled = false;
    api.proposals
      .list('pending', 50)
      .then((r) => {
        if (cancelled) return;
        const proposals = r.proposals || [];
        setPendingCounts({
          capital: proposals.filter((pr) => pr.family === 'capital').length,
          total: proposals.length,
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [variant]);

  const liveConsequence = (target: AutonomyLevel): string => {
    if (!pendingCounts) return '';
    const { capital, total } = pendingCounts;
    if (total === 0) {
      return 'Nothing is pending right now — this changes how future actions are handled.';
    }
    if (target === 'manual') {
      return `Right now: ${total} pending action${total === 1 ? '' : 's'} — all will keep waiting for your approval.`;
    }
    if (target === 'bounded') {
      return capital > 0
        ? `Right now: ${capital} pending capital action${capital === 1 ? '' : 's'} would become eligible to auto-execute within your ceiling on the next wake.`
        : `Right now: ${total} pending action${total === 1 ? '' : 's'} (none capital) — substrate writes still wait for you.`;
    }
    // autonomous
    return `Right now: ${total} pending action${total === 1 ? '' : 's'} would become eligible to execute without you.`;
  };

  if (variant === 'chip') {
    if (loading || !effectiveLevel) return null;
    const levelMeta = LEVELS.find(l => l.value === effectiveLevel);
    return (
      <button
        type="button"
        onClick={onOpen}
        className={cn(
          'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
          'bg-muted/60 text-muted-foreground hover:text-foreground transition-colors',
          className,
        )}
        title="Autonomy — click to manage"
      >
        <ShieldCheck className="w-3 h-3" />
        {levelMeta?.label ?? effectiveLevel}
      </button>
    );
  }

  if (variant === 'compact') {
    const levelMeta = LEVELS.find(l => l.value === effectiveLevel);
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Autonomy</h3>
        </div>
        {loading ? (
          <p className="text-xs text-muted-foreground/40">Loading…</p>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <div>
              <span className="text-sm font-medium">{levelMeta?.label ?? 'Not set'}</span>
              {levelMeta && (
                <p className="text-xs text-muted-foreground/70 mt-0.5">{levelMeta.description}</p>
              )}
            </div>
            {onOpen && (
              <button type="button" onClick={onOpen}
                className="shrink-0 text-xs text-muted-foreground hover:text-foreground transition-colors">
                Change <ArrowRight className="inline w-3 h-3" />
              </button>
            )}
          </div>
        )}
      </div>
    );
  }

  // full
  const currentLevel = effectiveLevel ?? 'manual';
  const pendingMeta = pendingLevel ? LEVELS.find(l => l.value === pendingLevel) : null;
  const currentMeta = LEVELS.find(l => l.value === currentLevel);

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">Autonomy</p>
          <p className="text-xs text-muted-foreground mt-0.5">How much YARNNN decides without asking first.</p>
        </div>
        <RevisionFootnote revision={lastRevision ?? null} className="shrink-0 pt-1" />
      </div>

      {loading ? (
        <div className="h-24 rounded-md bg-muted/30 animate-pulse" />
      ) : (
        <div className="space-y-2">
          {LEVELS.map(lvl => {
            const isActive = currentLevel === lvl.value;
            return (
              <button
                key={lvl.value}
                type="button"
                onClick={() => {
                  // No-op on selecting the already-active level (avoids
                  // pointless confirm-modal pops).
                  if (lvl.value === currentLevel) return;
                  setPendingLevel(lvl.value);
                }}
                className={cn(
                  'w-full text-left rounded-lg border px-4 py-3 transition-colors',
                  isActive
                    ? 'border-primary/50 bg-primary/5'
                    : 'border-border/60 hover:border-border hover:bg-muted/20',
                )}
              >
                <div className="flex items-center gap-2">
                  <div className={cn(
                    'h-3.5 w-3.5 rounded-full border-2 shrink-0 transition-colors',
                    isActive ? 'border-primary bg-primary' : 'border-border',
                  )} />
                  <span className="text-sm font-medium">{lvl.label}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1 ml-5.5">{lvl.description}</p>
              </button>
            );
          })}

          {meta?.default_ceiling_cents && currentLevel === 'bounded' && (
            <p className="text-[11px] text-muted-foreground/60 px-1">
              Ceiling: ${(meta.default_ceiling_cents / 100).toLocaleString()} per action
            </p>
          )}
        </div>
      )}

      {/* ADR-338 D4.2: the never_auto hard-safety list — the override that
          ALWAYS routes a matching action to the Queue regardless of the dial
          above. Surfacing it here makes the kernel-enforced-but-invisible
          failure class (and the duplicate-key-shadow) structurally
          impossible: the operator sees + edits the same list the kernel
          enforces, written through serialize() exactly once. */}
      {!loading && <NeverAutoEditor entries={meta?.default_never_auto ?? []} onSave={setNeverAuto} />}

      <ConfirmDialChange
        open={pendingLevel !== null && pendingMeta !== undefined}
        dialName="autonomy"
        fromLabel={currentMeta?.label ?? 'current'}
        toLabel={pendingMeta?.label ?? ''}
        consequence={
          pendingLevel
            ? [pendingMeta?.consequence ?? '', liveConsequence(pendingLevel)].filter(Boolean).join(' ')
            : (pendingMeta?.consequence ?? '')
        }
        onCancel={() => setPendingLevel(null)}
        onConfirm={async () => {
          if (!pendingLevel) return;
          const next = pendingLevel;
          setPendingLevel(null);
          await setLevel(next);
        }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// NeverAutoEditor — ADR-338 D4.2 hard-safety list
// ---------------------------------------------------------------------------
//
// Structured list editor (no hand-typed YAML). Each entry is either a bare
// action-type substring (e.g. `retraction`) or a `path:`-prefixed substrate
// path (e.g. `path: constitution/`). Add via the input, remove via the X.
// Saves the whole post-edit set through useAutonomy.setNeverAuto — which
// serializes it structurally, eliminating the opaque-body + duplicate-key
// shadow. Direct-manipulation contract (the act changes what the operation
// may auto-do — above the consent line).

function NeverAutoEditor({
  entries,
  onSave,
}: {
  entries: string[];
  onSave: (entries: string[]) => Promise<void>;
}) {
  const [draft, setDraft] = useState('');
  const [pathPrefix, setPathPrefix] = useState(false);
  const [saving, setSaving] = useState(false);

  const add = async () => {
    const raw = draft.trim();
    if (!raw) return;
    const entry = pathPrefix ? `path: ${raw.replace(/^path:\s*/, '')}` : raw;
    if (entries.includes(entry)) {
      setDraft('');
      return;
    }
    setSaving(true);
    try {
      await onSave([...entries, entry]);
      setDraft('');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (entry: string) => {
    setSaving(true);
    try {
      await onSave(entries.filter((e) => e !== entry));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-border/60 px-4 py-3 space-y-2">
      <div className="flex items-center gap-1.5">
        <Lock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <h4 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Never auto-execute
        </h4>
      </div>
      <p className="text-[11px] text-muted-foreground/70">
        Hard safety overrides. A matching action always waits for your approval — regardless of the
        level above. Add an action type (e.g. <code className="text-[10px]">retraction</code>) or a path
        (e.g. <code className="text-[10px]">constitution/</code>).
      </p>

      {entries.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5">
          {entries.map((entry) => (
            <li
              key={entry}
              className="inline-flex items-center gap-1 rounded-full bg-muted/60 px-2 py-0.5 text-[11px] font-medium text-foreground/80"
            >
              <span className="font-mono text-[10px]">{entry}</span>
              <button
                type="button"
                onClick={() => remove(entry)}
                disabled={saving}
                aria-label={`Remove ${entry}`}
                className="text-muted-foreground hover:text-foreground disabled:opacity-40"
              >
                <X className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[11px] text-muted-foreground/40 italic">
          No overrides — actions follow the level above.
        </p>
      )}

      <div className="flex items-center gap-1.5 pt-0.5">
        <button
          type="button"
          onClick={() => setPathPrefix((p) => !p)}
          className={cn(
            'shrink-0 rounded-md px-1.5 py-1 text-[10px] font-medium transition-colors',
            pathPrefix
              ? 'bg-primary/10 text-primary'
              : 'bg-muted/40 text-muted-foreground hover:text-foreground',
          )}
          title="Toggle: match by substrate path instead of action type"
        >
          {pathPrefix ? 'path:' : 'type'}
        </button>
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              void add();
            }
          }}
          placeholder={pathPrefix ? 'constitution/' : 'retraction'}
          disabled={saving}
          className="flex-1 rounded-md border border-border/60 bg-transparent px-2 py-1 text-xs outline-none focus:border-border disabled:opacity-40"
        />
        <button
          type="button"
          onClick={() => void add()}
          disabled={saving || !draft.trim()}
          className="shrink-0 inline-flex items-center gap-1 rounded-md bg-muted/60 px-2 py-1 text-[11px] font-medium hover:bg-muted disabled:opacity-40"
        >
          <Plus className="h-3 w-3" /> Add
        </button>
      </div>
    </div>
  );
}
