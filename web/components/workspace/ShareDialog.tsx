'use client';

/**
 * ShareDialog — the ONE place a share is minted in the cockpit (ADR-529 D1,
 * executing ADR-515 D2/D7).
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
 * It carries exactly four things, and deliberately nothing else:
 *   1. the two shapes stated as CONSEQUENCE — and no default fires without a
 *      click, which is what kills the over-grant by construction;
 *   2. the minted URL, VISIBLE and selectable, with an explicit Copy control;
 *   3. this file's live links, with revoke in place;
 *   4. nothing else — not the standing grant state (that is the rail:
 *      Workspace Settings -> Access, ADR-515 D6), not Export (ADR-515 D5: the
 *      boundary between a revocable grant and an irreversible copy must be
 *      impossible to confuse, so they never share a surface).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check, Copy, Link2, Loader2 } from 'lucide-react';

import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

type ShareRole = 'member' | 'viewer';

type ShareRow = {
  id: string;
  artifact_path: string | null;
  role: string;
  status: string;
  share_link?: string | null;
};

export interface ShareDialogProps {
  /** The artifact being shared. Absent = closed. */
  target: { path: string; name: string } | null;
  onClose: () => void;
}

/** The two shapes, as the operator reads them — consequence first, never a
 *  permission noun. ADR-529 D1.1 / ADR-465 D3. */
const SHAPES: Array<{ role: ShareRole; label: string; consequence: string }> = [
  {
    role: 'viewer',
    label: 'View only',
    consequence: 'They see this file and its history. They cannot change anything.',
  },
  {
    role: 'member',
    label: 'Full access',
    consequence: 'They join your workspace and can work in it — every change signed.',
  },
];

export function ShareDialog({ target, onClose }: ShareDialogProps) {
  const [role, setRole] = useState<ShareRole | null>(null);
  const [minting, setMinting] = useState(false);
  const [minted, setMinted] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [links, setLinks] = useState<ShareRow[] | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);
  const linkRef = useRef<HTMLInputElement>(null);

  const path = target?.path ?? null;

  // ADR-517 D5: `artifact_path` is stored in ONE canonical spelling (absolute,
  // normalized at create_share, backfilled by migration 234). The FE compares
  // raw. The old `shareKey()` normalizer in NodeDetailsPanel was named dead
  // defence by D5 and is deleted in this commit — comparing raw is now correct,
  // and keeping a normalizer would hide it if that ever stopped being true.
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
    setMinted(null);
    setCopied(false);
    setError(null);
    setLinks(null);
    void loadLinks();
  }, [target, loadLinks]);

  // Escape closes. An outclick does NOT — see the header comment.
  useEffect(() => {
    if (!target) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [target, onClose]);

  const mint = useCallback(async () => {
    if (!path || !target || !role) return;
    setMinting(true);
    setError(null);
    try {
      const res = await api.workspace.createShare(path, target.name, undefined, role);
      setMinted(res.share_link ?? null);
      // Copy on MINT (the operator asked for a link), but the field stays on
      // screen either way — a link you cannot see is one you cannot verify.
      if (res.share_link && typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(res.share_link).then(
          () => setCopied(true),
          () => { /* clipboard denied — the visible field is the fallback */ },
        );
      }
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

  const copy = useCallback(async () => {
    if (!minted) return;
    try {
      await navigator.clipboard.writeText(minted);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      linkRef.current?.select();
    }
  }, [minted]);

  const revoke = useCallback(async (id: string) => {
    setRevoking(id);
    try {
      await api.workspace.revokeShare(id);
      if (minted && links?.find((l) => l.id === id)?.share_link === minted) setMinted(null);
      await loadLinks();
    } catch {
      /* the row stays; the next load shows the truth */
    } finally {
      setRevoking(null);
    }
  }, [loadLinks, minted, links]);

  if (!target) return null;

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

          {/* ── 1. The choice, as consequence. Nothing is pre-selected: the
                 over-grant died here (ADR-529 D1). ── */}
          <div className="mt-4 space-y-1.5">
            {SHAPES.map((s) => (
              <button
                key={s.role}
                type="button"
                onClick={() => { setRole(s.role); setMinted(null); setCopied(false); }}
                aria-pressed={role === s.role}
                className={cn(
                  'w-full rounded-md border px-3 py-2 text-left transition-colors',
                  role === s.role
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:bg-muted/50',
                )}
              >
                <span className="block text-sm font-medium text-foreground">{s.label}</span>
                <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">
                  {s.consequence}
                </span>
              </button>
            ))}
          </div>

          {/* ── 2. The URL — up front, readable, copyable (the operator's
                 "explicitly show the URL Link with clear buttons"). ── */}
          {minted && (
            <div className="mt-4">
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Link
              </label>
              <div className="flex items-center gap-1.5">
                <input
                  ref={linkRef}
                  readOnly
                  value={minted}
                  onFocus={(e) => e.currentTarget.select()}
                  className="min-w-0 flex-1 rounded-md border border-border bg-background px-2.5 py-1.5 font-mono text-xs text-foreground outline-none focus:border-primary"
                  aria-label="Share link"
                />
                <button
                  type="button"
                  onClick={() => void copy()}
                  className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-foreground transition-colors hover:bg-muted/60"
                >
                  {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">
                Anyone with this link can open it — no account needed to read.
                {role === 'viewer' ? ' They cannot change anything.' : ' Accepting joins your workspace.'}
              </p>
            </div>
          )}

          {error && <p className="mt-3 text-xs text-destructive">{error}</p>}

          {/* ── 3. What is already out there, revocable in place. ── */}
          {links && links.length > 0 && (
            <div className="mt-4 border-t border-border/60 pt-3">
              <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Active links to this file
              </p>
              <ul className="space-y-1">
                {links.map((l) => (
                  <li key={l.id} className="flex items-center gap-2 text-xs">
                    <Link2 className="h-3 w-3 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate text-muted-foreground">
                      {l.role === 'viewer' ? 'View only' : 'Full access'}
                    </span>
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
              {minted ? 'Done' : 'Cancel'}
            </button>
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
              {minted ? 'Create another' : 'Create link'}
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
