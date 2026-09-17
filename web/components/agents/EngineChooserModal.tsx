'use client';

/**
 * EngineChooserModal — choosing the engine behind an agent (ADR-654 D4).
 *
 * WHY THIS REPLACED A DROPDOWN (operator, 2026-09-17: *"dropdown makes
 * switching almost too easy"*). A native `<select>` COMMITS ON CHANGE, and
 * `change` fires from a stray scroll, an arrow key, or a mistaken click — so
 * re-pointing an agent's engine, a decision that changes how it works for
 * every new conversation, could happen by accident with no confirm and no
 * undo. The mechanics are unchanged (same key, same narrowing, same
 * new-conversations-only rule); what changes is that the act is now
 * DELIBERATE: pick, then confirm, and Cancel leaves everything as it was.
 *
 * This is the ADR-651 posture applied to a write rather than a wait — the act
 * that is hard to reverse says so before it happens, not after.
 *
 * GROUPED BY PROVIDER, deliberately. A flat list of nine labels reads as nine
 * interchangeable things; grouped, a member sees they are choosing a VENDOR as
 * much as a model — which is the whole point of ADR-654's provider-neutrality.
 * The grouping is DERIVED from the id's own prefix (`anthropic/…`), never a
 * hand-kept table: a new provider groups itself, and a second home for
 * "which provider is this" is the ADR-562 drift this codebase keeps deleting.
 *
 * An unavailable engine is SHOWN, disabled, with its reason (ADR-559 D3 /
 * ADR-647 D8) — never filtered, so a member learns why rather than watching a
 * row vanish.
 */

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG, dismissModal } from '@/lib/shell/z-tiers';

export type EngineRow = {
  id: string;
  label: string;
  available?: boolean;
  unavailable_reason?: string | null;
  unavailable_detail?: string | null;
};

/** The provider's display name, derived from the routing id's own prefix.
 *  An unknown prefix falls back to the prefix itself rather than to a bucket
 *  named "Other": a new provider should read as itself the day it lands, with
 *  no edit here. */
const PROVIDER_NAMES: Record<string, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  gemini: 'Google',
  deepseek: 'DeepSeek',
  xai: 'xAI',
};

function providerOf(id: string): string {
  const prefix = id.split('/')[0] ?? '';
  return PROVIDER_NAMES[prefix] ?? prefix;
}

interface Props {
  open: boolean;
  onClose: () => void;
  /** The agent whose engine is being chosen — named in the dialog, because a
   *  modal that says "choose an engine" with no subject is a modal a member
   *  can open from the wrong row and never notice. */
  agentName: string;
  models: EngineRow[];
  /** What runs the agent today: the override if set, else the declared engine. */
  current: string;
  /** The kernel's declared engine — named on the "default" row so going back
   *  is a real choice rather than an unlabelled escape hatch. */
  declared: string;
  /** Which engine the member has explicitly chosen, if any. */
  override?: string | null;
  /** null clears the override. Rejects → the caller surfaces the failure. */
  onConfirm: (model: string | null) => Promise<void>;
}

export function EngineChooserModal({
  open, onClose, agentName, models, current, declared, override, onConfirm,
}: Props) {
  // The PENDING selection — the whole point of the modal. Nothing is written
  // until Confirm, so a mis-click costs a Cancel rather than a re-point.
  const [picked, setPicked] = useState<string | null>(override ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-seed on every open: a stale pending value from a previous visit would
  // silently preselect something the member never chose this time.
  useEffect(() => {
    if (open) {
      setPicked(override ?? null);
      setError(null);
    }
  }, [open, override]);

  if (!open) return null;

  const labelFor = (id: string) => models.find((m) => m.id === id)?.label ?? id;
  const dirty = (picked ?? null) !== (override ?? null);

  const confirm = async () => {
    if (!dirty) return onClose();
    setBusy(true);
    setError(null);
    try {
      await onConfirm(picked);
      onClose();
    } catch {
      setError('That did not save. Nothing changed — try again.');
    } finally {
      setBusy(false);
    }
  };

  // Grouped by provider, each group in the order the server served it. The
  // server's order is meaningful (frontier first within a vendor) and
  // re-sorting here would invent a ranking the registry did not state.
  const groups: { provider: string; rows: EngineRow[] }[] = [];
  for (const m of models) {
    const provider = providerOf(m.id);
    const last = groups.find((g) => g.provider === provider);
    if (last) last.rows.push(m);
    else groups.push({ provider, rows: [m] });
  }

  const Row = ({
    id, label, disabled, note,
  }: { id: string | null; label: string; disabled?: boolean; note?: string }) => {
    const selected = (picked ?? null) === id;
    return (
      <button
        type="button"
        role="radio"
        aria-checked={selected}
        disabled={disabled || busy}
        onClick={() => setPicked(id)}
        className={cn(
          'flex w-full items-start gap-2.5 rounded-md border px-3 py-2 text-left transition-colors',
          selected ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/50',
          (disabled || busy) && 'cursor-not-allowed opacity-50 hover:bg-transparent',
        )}
      >
        <span
          aria-hidden
          className={cn(
            'mt-[3px] h-3.5 w-3.5 shrink-0 rounded-full border',
            selected ? 'border-[4px] border-primary' : 'border-border',
          )}
        />
        <span className="min-w-0">
          <span className="block text-sm text-foreground">{label}</span>
          {note && <span className="block text-[11px] text-muted-foreground">{note}</span>}
        </span>
      </button>
    );
  };

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={dismissModal(onClose)}
      />
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto flex max-h-[80vh] w-full max-w-md flex-col rounded-lg border border-border bg-card shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
          aria-label={`Engine for ${agentName}`}
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}
        >
          <div className="border-b border-border/60 p-5 pb-3">
            <h3 className="text-base font-semibold text-card-foreground">
              Engine for {agentName}
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Runs {agentName} in new conversations. Ones already running keep the
              engine they started with.
            </p>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-5 pt-3" role="radiogroup">
            <Row
              id={null}
              label={declared ? `Default — ${labelFor(declared)}` : 'Default'}
              note="What yarnnn chose for this agent."
            />
            {groups.map((g) => (
              <div key={g.provider} className="mt-4 space-y-1.5">
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
                  {g.provider}
                </p>
                {g.rows.map((m) => (
                  <Row
                    key={m.id}
                    id={m.id}
                    label={m.label}
                    disabled={m.available === false}
                    note={
                      m.available === false
                        ? m.unavailable_detail || 'Not available right now'
                        : undefined
                    }
                  />
                ))}
              </div>
            ))}
          </div>

          <div className="border-t border-border/60 p-5 pt-3">
            {error && <p className="mb-2 text-[11px] text-destructive">{error}</p>}
            <div className="flex items-center justify-between gap-3">
              <p className="min-w-0 text-[11px] text-muted-foreground">
                {dirty ? (
                  <>Now: {labelFor(current)} → {picked ? labelFor(picked) : labelFor(declared)}</>
                ) : (
                  <>Running {labelFor(current)}</>
                )}
              </p>
              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  onClick={dismissModal(onClose)}
                  disabled={busy}
                  className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!dirty || busy}
                  onClick={() => void confirm()}
                  className={cn(
                    'rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                    dirty && !busy
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                      : 'cursor-not-allowed bg-muted text-muted-foreground',
                  )}
                >
                  {busy ? 'Saving…' : 'Change engine'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
