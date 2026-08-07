'use client';

/**
 * ShareDialog — the ONE place a share is minted in the cockpit (ADR-529 D1,
 * executing ADR-515 D2/D7), and the one place a live link is HANDED BACK
 * (ADR-534 D1/D3).
 *
 * WHAT THIS REPLACES (ADR-529 D4 — deleted, not deprecated): three fragments of
 * one act, none complete, no two agreeing —
 *
 *   Files      one click -> minted AND copied, role ALWAYS 'member', with a
 *              toast announcing "anyone with it can join the workspace": a
 *              decision the operator was never asked to make (the over-grant).
 *   Studio     an outclick-dismissible popover offering the two shapes, whose
 *              own copy pointed at "Files" for management — a surface that
 *              never managed shares.
 *   Properties the list + revoke, in a third place entirely.
 *
 * The operator's rule of thumb is the design constraint: "the concept should
 * feel the same for the user regardless of ANY surface." So this mounts from
 * the FileVerbs bundle (ADR-514 D2.6) and every file surface inherits the
 * identical act — tree, grid, listing, Files, Studio.
 *
 * A MODAL, not a popover: minting a grant is governance (ADR-517 §1.3), and a
 * governance act that vanishes on a stray outclick is misreporting its own
 * weight. Escape and Cancel dismiss; an incidental click does not.
 *
 * ── ADR-534: THE LINK IS A STANDING ADDRESS ───────────────────────────────
 *
 * A live link is durable (`expires_at` is NULL on everything the cockpit
 * mints), reusable, and resolves to the file's CURRENT content on every read.
 * The prior cut rendered it as a footnote whose only affordance was Revoke,
 * while a link minted ten seconds earlier got a labeled field and a Copy
 * button — the same object, valued only while new, so the path of least
 * resistance was minting a duplicate.
 *
 * So: the dialog OPENS ON WHAT EXISTS. A shape with a live link shows that
 * link. Minting a second one of the same shape is deliberate, never the
 * default gesture.
 *
 * And it is HONEST when the address stops resolving. The share row is not
 * chased through moves/renames (ADR-534 §3 — the reference is a historical
 * fact, exactly as ADR-448 ruled for the derive edge). Brokenness is DERIVED
 * at read time by the same resolution the public boundary performs, so no
 * relocation verb has to remember anything and none can desync it.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle, Check, Copy, Loader2 } from 'lucide-react';

import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

type ShareRole = 'member' | 'viewer';

type ShareRow = {
  id: string;
  artifact_path: string | null;
  role: string;
  status: string;
  created_at?: string;
  share_link?: string | null;
};

export interface ShareDialogProps {
  /** The artifact being shared. Absent = closed. */
  target: { path: string; name: string } | null;
  onClose: () => void;
}

/** The two shapes, as the operator reads them — consequence first, never a
 *  permission noun. ADR-529 D1.1 / ADR-465 D3.
 *
 *  ADR-534 D5 — the copy states two things the operator was NOT being told,
 *  both measured against behaviour:
 *
 *   - PERMANENCE. `expires_at` is NULL on every cockpit-minted link, and the
 *     preview resolves content live on every request. For view-only that
 *     durability IS the feature, so it is said out loud.
 *   - TRANSFERABILITY. There is no email lock (that is Invite, a different
 *     door — `accept_share` takes ANY authenticated principal). A full-access
 *     link pasted into a channel lets every reader there join. */
const SHAPES: Array<{
  role: ShareRole;
  label: string;
  consequence: string;
  standing: string;
}> = [
  {
    role: 'viewer',
    label: 'View only',
    consequence: 'They see this file and its history. They cannot change anything.',
    standing: 'Anyone with this link sees the current version, always — until you revoke it.',
  },
  {
    role: 'member',
    label: 'Full access',
    consequence: 'They join your workspace and can work in it — every change signed.',
    standing: 'Anyone this link reaches can join — it works for whoever holds it, not just the person you send it to.',
  },
];

function mintedWhen(iso?: string): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

export function ShareDialog({ target, onClose }: ShareDialogProps) {
  const [role, setRole] = useState<ShareRole | null>(null);
  const [minting, setMinting] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [links, setLinks] = useState<ShareRow[] | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);
  /** Set once the operator deliberately asks for a SECOND link of a shape that
   *  already has one — the escape hatch that keeps per-recipient links
   *  expressible (ADR-534 D1) without making duplication the default. */
  const [forceMint, setForceMint] = useState(false);
  /** ADR-534 D4 — does this file still exist at the path the links name? */
  const [stale, setStale] = useState(false);
  const linkRef = useRef<HTMLInputElement>(null);

  const path = target?.path ?? null;

  // ADR-517 D5: `artifact_path` is stored in ONE canonical spelling (absolute,
  // normalized at create_share, backfilled by migration 234). The FE compares
  // raw. The old `shareKey()` normalizer in NodeDetailsPanel was named dead
  // defence by D5 and is deleted — comparing raw is now correct, and keeping a
  // normalizer would hide it if that ever stopped being true.
  const loadLinks = useCallback(async () => {
    if (!path) return;
    try {
      const r = await api.workspace.listShares();
      setLinks(r.shares.filter((s) => s.artifact_path === path && s.status === 'active'));
    } catch {
      setLinks(null);
    }
  }, [path]);

  useEffect(() => {
    if (!target) return;
    setRole(null);
    setCopied(null);
    setError(null);
    setLinks(null);
    setForceMint(false);
    setStale(false);
    void loadLinks();
  }, [target, loadLinks]);

  // ADR-534 D4 — the operator learns their links are dark AT THE MOMENT they
  // look, not from a recipient's confused message. Derived, never stored: this
  // asks the same question the public boundary asks (does a live file sit at
  // this path?), so a move that never heard of shares cannot desync it.
  //
  // Deliberately NOT a share-specific endpoint — reading the file's own listing
  // is the resolution, and inventing a "is my share broken" API would be the
  // maintained-reference this ADR refused.
  useEffect(() => {
    if (!target || !path) return;
    let cancelled = false;
    void (async () => {
      try {
        await api.workspace.getFile(path);
        if (!cancelled) setStale(false);
      } catch (e) {
        // `GET /api/workspace/file` raises a real 404 for a path with no live
        // row (routes/workspace.py:784) — THAT is the signal, and the only one.
        // Anything else (403, 500, offline) is INCONCLUSIVE and must not be
        // reported as breakage: telling an operator a healthy link is broken is
        // the same dishonesty in the other direction, and it would make them
        // revoke a link that works.
        if (!cancelled && e instanceof APIError && e.status === 404) setStale(true);
      }
    })();
    return () => { cancelled = true; };
  }, [target, path]);

  // Escape closes. An outclick does NOT — see the header comment.
  useEffect(() => {
    if (!target) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [target, onClose]);

  /** ADR-534 D1 — the reuse lookup keys on (path, ROLE), never path alone.
   *  A file may hold both shapes at once; a path-only match would hand a
   *  view-only requester a full-access link. This is the load-bearing detail
   *  of the decision, and the gate asserts it over a live/live, live/none,
   *  none/none matrix. */
  const liveFor = useCallback(
    (r: ShareRole): ShareRow | null =>
      links?.find((l) => l.role === r && l.share_link) ?? null,
    [links],
  );

  /** The link this dialog is currently handing back: the live one for the
   *  selected shape unless the operator asked for a fresh one. */
  const shown = useMemo(() => {
    if (!role || forceMint) return null;
    return liveFor(role);
  }, [role, forceMint, liveFor]);

  const mint = useCallback(async () => {
    if (!path || !target || !role) return;
    setMinting(true);
    setError(null);
    try {
      const res = await api.workspace.createShare(path, target.name, undefined, role);
      if (res.share_link && typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(res.share_link).then(
          () => setCopied(res.share_link ?? null),
          () => { /* clipboard denied — the visible field is the fallback */ },
        );
      }
      // Fold the new link into the list and stop forcing: the dialog returns to
      // showing what EXISTS, which now includes this one.
      setForceMint(false);
      await loadLinks();
    } catch (e) {
      const data = e instanceof APIError ? (e.data as { detail?: unknown } | undefined) : undefined;
      setError(
        typeof data?.detail === 'string'
          ? data.detail
          : 'Could not create the link. Try again.',
      );
    } finally {
      setMinting(false);
    }
  }, [path, target, role, loadLinks]);

  const copy = useCallback(async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(url);
      setTimeout(() => setCopied((c) => (c === url ? null : c)), 2000);
    } catch {
      linkRef.current?.select();
    }
  }, []);

  const revoke = useCallback(async (id: string) => {
    setRevoking(id);
    try {
      await api.workspace.revokeShare(id);
      await loadLinks();
    } catch {
      /* the row stays; the next load shows the truth */
    } finally {
      setRevoking(null);
    }
  }, [loadLinks]);

  if (!target) return null;

  const shape = SHAPES.find((s) => s.role === role);

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
      />
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto w-full max-w-md rounded-lg border border-border bg-card p-5 shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
          aria-label={`Share ${target.name}`}
        >
          <h3 className="text-base font-semibold text-card-foreground">Share</h3>
          <p className="mt-1 truncate text-xs text-muted-foreground" title={target.name}>
            {target.name}
          </p>

          {/* ── ADR-534 D4 — the file is gone; every link below is dark. Said
                 at the top, because it changes what everything under it means. ── */}
          {stale && (
            <div className="mt-3 flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-500" />
              <p className="text-[11px] leading-snug text-foreground/80">
                This file has been moved, renamed, or deleted. Links below still exist but no
                longer open anything — anyone using one sees a message saying so. Revoke them, or
                share the file again from its new location.
              </p>
            </div>
          )}

          {/* ── 1. The choice, as consequence. Nothing is pre-selected: the
                 over-grant died here (ADR-529 D1). A shape that already has a
                 live link says so ON the card (ADR-534 D1). ── */}
          <div className="mt-4 space-y-1.5">
            {SHAPES.map((s) => {
              const live = liveFor(s.role);
              return (
                <button
                  key={s.role}
                  type="button"
                  onClick={() => { setRole(s.role); setForceMint(false); setCopied(null); }}
                  aria-pressed={role === s.role}
                  className={cn(
                    'w-full rounded-md border px-3 py-2 text-left transition-colors',
                    role === s.role
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:bg-muted/50',
                  )}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{s.label}</span>
                    {live && (
                      <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                        {stale ? 'link broken' : 'link active'}
                      </span>
                    )}
                  </span>
                  <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">
                    {s.consequence}
                  </span>
                </button>
              );
            })}
          </div>

          {/* ── 2. The link, handed back. Whether it was minted ten seconds ago
                 or last week, it renders the SAME — that is the whole of
                 ADR-534 D1. ── */}
          {shown?.share_link && (
            <div className="mt-4">
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Link
              </label>
              <div className="flex items-center gap-1.5">
                <input
                  ref={linkRef}
                  readOnly
                  value={shown.share_link}
                  onFocus={(e) => e.currentTarget.select()}
                  className="min-w-0 flex-1 rounded-md border border-border bg-background px-2.5 py-1.5 font-mono text-xs text-foreground outline-none focus:border-primary"
                  aria-label="Share link"
                />
                <button
                  type="button"
                  onClick={() => void copy(shown.share_link!)}
                  className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-foreground transition-colors hover:bg-muted/60"
                >
                  {copied === shown.share_link
                    ? <Check className="h-3.5 w-3.5" />
                    : <Copy className="h-3.5 w-3.5" />}
                  {copied === shown.share_link ? 'Copied' : 'Copy'}
                </button>
              </div>
              {/* ADR-534 D5 — permanence and transferability, stated. */}
              <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">
                {stale
                  ? 'This link no longer opens anything — the file it names is gone.'
                  : shape?.standing}
              </p>
              {/* The escape hatch: a second link of this shape stays reachable
                  (per-recipient links are the reason the transport is
                  link-based) but is never the default gesture. */}
              <button
                type="button"
                onClick={() => { setForceMint(true); setCopied(null); }}
                className="mt-2 text-[11px] text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
              >
                Create a separate link
              </button>
            </div>
          )}

          {error && <p className="mt-3 text-xs text-destructive">{error}</p>}

          {/* ── 3. Every live link to this file — each one COPYABLE, not only
                 revocable. An operator could previously destroy a link they
                 could not read (ADR-534 D3). ── */}
          {links && links.length > 0 && (
            <div className="mt-4 border-t border-border/60 pt-3">
              <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Active links to this file
              </p>
              <ul className="space-y-1">
                {links.map((l) => (
                  <li key={l.id} className="flex items-center gap-2 text-xs">
                    <span className="min-w-0 flex-1 truncate text-muted-foreground">
                      {l.role === 'viewer' ? 'View only' : 'Full access'}
                      {l.created_at && (
                        <span className="ml-1.5 text-[10px] opacity-70">
                          {mintedWhen(l.created_at)}
                        </span>
                      )}
                    </span>
                    {l.share_link && (
                      <button
                        type="button"
                        onClick={() => void copy(l.share_link!)}
                        className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {copied === l.share_link ? 'Copied' : 'Copy'}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => void revoke(l.id)}
                      disabled={revoking === l.id}
                      className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground transition-colors hover:text-destructive disabled:opacity-50"
                    >
                      {revoking === l.id ? 'Revoking…' : 'Revoke'}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
            >
              {shown ? 'Done' : 'Cancel'}
            </button>
            {/* The primary action MINTS only when there is nothing to hand back
                (or the operator asked for another). On a file that already has
                a live link of the chosen shape, the dialog's job is done the
                moment it shows that link — so the button stops existing rather
                than sitting there reading "Create another", which is what made
                duplication the path of least resistance. */}
            {!shown && (
              <button
                type="button"
                disabled={!role || minting}
                onClick={() => void mint()}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                  role && !minting
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'cursor-not-allowed bg-muted text-muted-foreground',
                )}
              >
                {minting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Create link
              </button>
            )}
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
