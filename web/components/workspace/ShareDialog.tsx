'use client';

/**
 * ShareDialog — the ONE place a file's address is handed out and the ONE place
 * a person is brought into the workspace from a file (ADR-529 D1, ADR-534,
 * ADR-537).
 *
 * ── WHY TWO TABS (ADR-537) ────────────────────────────────────────────────
 *
 * The prior cut asked "how much access?" and offered View-only / Full-access as
 * peers over one link field. That asserts the two produce the same kind of
 * object. They do not:
 *
 *   View only     a PERMALINK to a document. The URL is the deliverable.
 *                 Terminal, grants nothing, one per file, reused forever.
 *   Full access   an OPEN ENROLLMENT OFFER. The URL is a COUPON for a
 *                 membership that has not happened yet — redeemable by anyone
 *                 holding it, repeatedly, each redemption billing a seat and
 *                 granting the WHOLE WORKSPACE (scopes=None → class default),
 *                 not this file.
 *
 * So the sheet asks WHAT YOU ARE DOING, and the tabs divide by SCOPE:
 *
 *   Link     about THIS FILE    — the simple default; nearly the whole dialog
 *   People   about THE WORKSPACE — governance, seats, secondary but complete
 *
 * The operator's constraint is the design: "i want share to feel very simple,
 * BUT, the invite flow is there as secondary."
 *
 * NOT Notion's Share/Publish tab — we deliberately have no publish act
 * (ADR-531 D3: publishing is distribution, sharing is interop). What is taken
 * from that reference is the BODY — a roster of who has access — which this
 * surface never had, and whose absence is why permission level was the only
 * thing left to ask about.
 *
 * ── WHAT SURVIVES FROM ADR-534 ────────────────────────────────────────────
 *
 * Reuse-first, unchanged, on the Link tab: a live link is a standing address
 * (durable, reusable, resolving to CURRENT content on every read), so the tab
 * opens on it rather than on a mint form. That axiom was right for an address
 * and wrong for an invitation; ADR-537 narrows it to the act it fits.
 *
 * Honest-when-broken, unchanged: the share row is NOT chased through
 * moves/renames (ADR-534 §3 — a historical reference, as ADR-448 ruled for the
 * derive edge). Brokenness is DERIVED at read time.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle, Check, Copy, Loader2 } from 'lucide-react';

import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

type ShareRole = 'member' | 'viewer';
type Tab = 'link' | 'people';

type ShareRow = {
  id: string;
  artifact_path: string | null;
  role: string;
  status: string;
  created_at?: string;
  share_link?: string | null;
  last_accepted_at?: string | null;
};

type ReachRow = {
  principal_id: string;
  role: string;
  label: string | null;
  can_read?: boolean | null;
  can_write?: boolean | null;
};

type InviteRow = {
  id: string;
  email: string;
  status: string;
  expires_at?: string;
};

export interface ShareDialogProps {
  /** The artifact being shared. Absent = closed. */
  target: { path: string; name: string } | null;
  onClose: () => void;
}

function shortDate(iso?: string | null): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

export function ShareDialog({ target, onClose }: ShareDialogProps) {
  const [tab, setTab] = useState<Tab>('link');
  const [copied, setCopied] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [links, setLinks] = useState<ShareRow[] | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [minting, setMinting] = useState(false);
  /** The deliberate second link of a shape that already has one (ADR-534 D1). */
  const [forceMint, setForceMint] = useState<ShareRole | null>(null);
  /** ADR-534 D4 — does this file still exist at the path the links name? */
  const [stale, setStale] = useState(false);
  // People tab
  const [reach, setReach] = useState<ReachRow[] | null>(null);
  const [invites, setInvites] = useState<InviteRow[] | null>(null);
  const [email, setEmail] = useState('');
  const [inviting, setInviting] = useState(false);
  const [inviteNote, setInviteNote] = useState<string | null>(null);
  const [showJoinLink, setShowJoinLink] = useState(false);
  const linkRef = useRef<HTMLInputElement>(null);

  const path = target?.path ?? null;

  // ADR-517 D5: `artifact_path` has ONE canonical spelling (absolute,
  // normalized at create_share). The FE compares raw — a normalizer here would
  // hide it if that ever stopped being true.
  const loadLinks = useCallback(async () => {
    if (!path) return;
    try {
      const r = await api.workspace.listShares();
      setLinks(r.shares.filter((s) => s.artifact_path === path && s.status === 'active'));
    } catch {
      setLinks(null);
    }
  }, [path]);

  const loadPeople = useCallback(async () => {
    if (!path) return;
    // ADR-537 D2 — `getMembers(path)` computes per-principal reach over THIS
    // path with the same powerbox matcher the gate consults, so the roster and
    // the gate cannot disagree. Relocated here from NodeDetailsPanel's
    // FileReach (MOVED, not copied — a second per-file reach surface is the
    // dual-surface problem ADR-529 D4 deleted).
    try {
      const r = await api.workspace.getMembers(path);
      setReach(r.members.filter((m) => m.can_read || m.can_write));
    } catch {
      setReach(null);
    }
    try {
      const r = await api.workspace.listInvites();
      setInvites(r.invites.filter((i) => i.status === 'pending'));
    } catch {
      // Invite LISTING stays owner-only (ADR-537 D3 widened creation, not the
      // roster) — a non-owner gets 403 here, which is not an error to report.
      setInvites(null);
    }
  }, [path]);

  useEffect(() => {
    if (!target) return;
    setTab('link');
    setCopied(null);
    setError(null);
    setLinks(null);
    setForceMint(null);
    setStale(false);
    setReach(null);
    setInvites(null);
    setEmail('');
    setInviteNote(null);
    setShowJoinLink(false);
    void loadLinks();
    void loadPeople();
  }, [target, loadLinks, loadPeople]);

  // ADR-534 D4 — the operator learns their links are dark AT THE MOMENT they
  // look. Derived, never stored: this asks the same question the public
  // boundary asks, so a move that never heard of shares cannot desync it.
  useEffect(() => {
    if (!target || !path) return;
    let cancelled = false;
    void (async () => {
      try {
        await api.workspace.getFile(path);
        if (!cancelled) setStale(false);
      } catch (e) {
        // Only a real 404 means the file is gone (routes/workspace.py). A
        // 403/500/offline is INCONCLUSIVE: calling a healthy link broken would
        // make an operator revoke one that works.
        if (!cancelled && e instanceof APIError && e.status === 404) setStale(true);
      }
    })();
    return () => { cancelled = true; };
  }, [target, path]);

  useEffect(() => {
    if (!target) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [target, onClose]);

  /** ADR-534 D1 — keyed on (path, ROLE), never path alone: a file may hold both
   *  shapes, and a path-only match hands back the wrong one. */
  const liveFor = useCallback(
    (r: ShareRole): ShareRow | null =>
      links?.find((l) => l.role === r && l.share_link) ?? null,
    [links],
  );

  const viewLink = useMemo(
    () => (forceMint === 'viewer' ? null : liveFor('viewer')),
    [forceMint, liveFor],
  );
  const joinLink = useMemo(
    () => (forceMint === 'member' ? null : liveFor('member')),
    [forceMint, liveFor],
  );

  /** ADR-537 D1 — the badge. Tabs hide things and the hidden one is the
   *  consequential one; without this an operator never learns a join link is
   *  live on this file. Both lists are already fetched, so it is free. */
  const peopleBadge = (invites?.length ?? 0) + (joinLink ? 1 : 0);

  const mint = useCallback(async (role: ShareRole) => {
    if (!path || !target) return;
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
      setForceMint(null);
      await loadLinks();
    } catch (e) {
      const data = e instanceof APIError ? (e.data as { detail?: unknown } | undefined) : undefined;
      setError(typeof data?.detail === 'string' ? data.detail : 'Could not create the link. Try again.');
    } finally {
      setMinting(false);
    }
  }, [path, target, loadLinks]);

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

  const invite = useCallback(async () => {
    const addr = email.trim();
    if (!addr) return;
    setInviting(true);
    setInviteNote(null);
    try {
      await api.workspace.inviteMember(addr);
      setEmail('');
      setInviteNote(`Invited ${addr}.`);
      await loadPeople();
    } catch (e) {
      const data = e instanceof APIError ? (e.data as { detail?: unknown } | undefined) : undefined;
      setInviteNote(
        typeof data?.detail === 'string' ? data.detail : 'Could not send that invite.',
      );
    } finally {
      setInviting(false);
    }
  }, [email, loadPeople]);

  if (!target) return null;

  const linkField = (row: ShareRow) => (
    <div className="flex items-center gap-1.5">
      <input
        ref={linkRef}
        readOnly
        value={row.share_link ?? ''}
        onFocus={(e) => e.currentTarget.select()}
        className="min-w-0 flex-1 rounded-md border border-border bg-background px-2.5 py-1.5 font-mono text-xs text-foreground outline-none focus:border-primary"
        aria-label="Share link"
      />
      <button
        type="button"
        onClick={() => void copy(row.share_link!)}
        className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-foreground transition-colors hover:bg-muted/60"
      >
        {copied === row.share_link ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        {copied === row.share_link ? 'Copied' : 'Copy'}
      </button>
    </div>
  );

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

          {/* ── The two tabs: this file · the workspace ── */}
          <div className="mt-4 flex gap-1 border-b border-border/60" role="tablist">
            {(['link', 'people'] as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                role="tab"
                aria-selected={tab === t}
                onClick={() => setTab(t)}
                className={cn(
                  'relative -mb-px border-b-2 px-3 py-1.5 text-sm transition-colors',
                  tab === t
                    ? 'border-primary font-medium text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                {t === 'link' ? 'Link' : 'People'}
                {t === 'people' && peopleBadge > 0 && (
                  <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                    {peopleBadge}
                  </span>
                )}
              </button>
            ))}
          </div>

          {stale && (
            <div className="mt-3 flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-500" />
              <p className="text-[11px] leading-snug text-foreground/80">
                This file has been moved, renamed, or deleted. Links to it still exist but no
                longer open anything — anyone using one sees a message saying so.
              </p>
            </div>
          )}

          {/* ══ LINK — about THIS FILE. The simple default. ══ */}
          {tab === 'link' && (
            <div className="mt-4">
              {viewLink?.share_link ? (
                <>
                  {linkField(viewLink)}
                  <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">
                    {stale
                      ? 'This link no longer opens anything — the file it names is gone.'
                      : 'Anyone with this link sees the current version, always — until you revoke it.'}
                  </p>
                  <div className="mt-2 flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => { setForceMint('viewer'); setCopied(null); }}
                      className="text-[11px] text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
                    >
                      Create a separate link
                    </button>
                    <button
                      type="button"
                      onClick={() => void revoke(viewLink.id)}
                      disabled={revoking === viewLink.id}
                      className="text-[11px] text-muted-foreground underline underline-offset-2 transition-colors hover:text-destructive disabled:opacity-50"
                    >
                      {revoking === viewLink.id ? 'Revoking…' : 'Revoke'}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-xs leading-snug text-muted-foreground">
                    A link anyone can open to read this file and its history. They cannot change
                    anything, and it keeps showing the current version until you revoke it.
                  </p>
                  <button
                    type="button"
                    disabled={minting}
                    onClick={() => void mint('viewer')}
                    className={cn(
                      'mt-3 inline-flex items-center gap-1.5 rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                      minting
                        ? 'cursor-not-allowed bg-muted text-muted-foreground'
                        : 'bg-primary text-primary-foreground hover:bg-primary/90',
                    )}
                  >
                    {minting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    Create link
                  </button>
                </>
              )}
              {error && <p className="mt-3 text-xs text-destructive">{error}</p>}
            </div>
          )}

          {/* ══ PEOPLE — about THE WORKSPACE. Secondary, complete. ══ */}
          {tab === 'people' && (
            <div className="mt-4 space-y-4">
              {/* Who can reach this file — the state, before any change. */}
              {((reach && reach.length > 0) || (invites && invites.length > 0)) && (
                <ul className="space-y-1">
                  {reach?.map((m) => (
                    <li key={m.principal_id} className="flex items-center gap-2 text-xs">
                      <span className="min-w-0 flex-1 truncate">
                        {m.label || m.principal_id}
                        <span className="ml-1 text-muted-foreground">({m.role})</span>
                      </span>
                      <span
                        className={cn(
                          'shrink-0 rounded px-1.5 py-0.5 text-[10px]',
                          m.can_write
                            ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
                            : 'bg-muted text-muted-foreground',
                        )}
                      >
                        {m.can_write ? 'can edit' : 'read-only'}
                      </span>
                    </li>
                  ))}
                  {invites?.map((i) => (
                    <li key={i.id} className="flex items-center gap-2 text-xs">
                      <span className="min-w-0 flex-1 truncate text-muted-foreground">
                        {i.email}
                      </span>
                      <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                        invited{i.expires_at ? ` · expires ${shortDate(i.expires_at)}` : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              {/* Bring someone in — email is the singular path (ADR-537 D3). */}
              <div className="border-t border-border/60 pt-3">
                <div className="flex items-center gap-1.5">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') void invite(); }}
                    placeholder="name@company.com"
                    className="min-w-0 flex-1 rounded-md border border-border bg-background px-2.5 py-1.5 text-xs text-foreground outline-none focus:border-primary"
                    aria-label="Invite by email"
                  />
                  <button
                    type="button"
                    onClick={() => void invite()}
                    disabled={!email.trim() || inviting}
                    className={cn(
                      'inline-flex shrink-0 items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                      email.trim() && !inviting
                        ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                        : 'cursor-not-allowed bg-muted text-muted-foreground',
                    )}
                  >
                    {inviting && <Loader2 className="h-3 w-3 animate-spin" />}
                    Invite
                  </button>
                </div>
                {/* ADR-537 D5 — workspace scope and seat cost, both previously silent. */}
                <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">
                  They&apos;ll get an email. Joining gives full access to this workspace and uses a
                  seat.
                </p>
                {inviteNote && (
                  <p className="mt-1.5 text-[11px] text-muted-foreground">{inviteNote}</p>
                )}
              </div>

              {/* The open join link — a disclosure, never a peer of the address. */}
              <div className="border-t border-border/60 pt-3">
                {joinLink?.share_link ? (
                  <>
                    <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      Open join link
                    </p>
                    {linkField(joinLink)}
                    {/* ADR-537 D4/D5 — redemption stated, forwardability stated, and
                        what revoke does NOT do stated. A redeemer's NAME is never
                        shown: the column is overwritten on every accept. */}
                    <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">
                      {joinLink.last_accepted_at
                        ? `Last joined ${shortDate(joinLink.last_accepted_at)}. `
                        : 'No one has joined yet. '}
                      Anyone this link reaches can join — it works for whoever holds it, not just
                      the person you send it to. Revoking closes the offer; it does not remove
                      anyone who already joined.
                    </p>
                    <button
                      type="button"
                      onClick={() => void revoke(joinLink.id)}
                      disabled={revoking === joinLink.id}
                      className="mt-2 text-[11px] text-muted-foreground underline underline-offset-2 transition-colors hover:text-destructive disabled:opacity-50"
                    >
                      {revoking === joinLink.id ? 'Closing…' : 'Close this offer'}
                    </button>
                  </>
                ) : showJoinLink ? (
                  <>
                    <p className="text-[11px] leading-snug text-muted-foreground">
                      A link anyone can use to join this workspace with full access. It works for
                      whoever holds it, not just the person you send it to, and it can be used more
                      than once.
                    </p>
                    <button
                      type="button"
                      disabled={minting}
                      onClick={() => void mint('member')}
                      className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-foreground transition-colors hover:bg-muted/60 disabled:opacity-50"
                    >
                      {minting && <Loader2 className="h-3 w-3 animate-spin" />}
                      Create open join link
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowJoinLink(true)}
                    className="text-[11px] text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
                  >
                    or create an open join link ›
                  </button>
                )}
              </div>

              {/* ADR-537 D2 — crosslinks ADR-515 D6's named half-view: this pane is
                  per-FILE, the rail is per-PRINCIPAL, and until now neither pointed
                  at the other. */}
              <p className="text-[11px] text-muted-foreground">
                Manage access in Workspace Settings →
              </p>
            </div>
          )}

          <div className="mt-5 flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
