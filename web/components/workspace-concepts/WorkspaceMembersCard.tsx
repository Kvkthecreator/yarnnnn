'use client';

/**
 * WorkspaceMembersCard — read-only legibility for the workspace's principals
 * (ADR-373 D2). The "who can write here, and what regions" view over
 * principal_grants.
 *
 * In the multi-principal model (ADR-373) a *member* is any authenticated
 * principal bound to the workspace by a grant: the human owner, other humans,
 * their agents, third-party platforms, and — crucially — foreign LLMs reaching
 * in over MCP (claude.ai, ChatGPT, Cursor, Copilot, …). An MCP connector IS a
 * member (a foreign-llm principal), which is why this panel is "Workspace
 * Members", not "Users".
 *
 * Governable (ADR-386): the grant table + consult ship per-principal
 * authorization; this surfaces the same facts the gate reads AND lets the
 * operator govern existing members — NARROW a member's write-region, or REVOKE
 * (full eviction: grant revoked + OAuth tokens deleted, must reconnect). The
 * owner grant is immutable here (D4 — no self-lockout). Foreign-LLM members
 * auto-provision on OAuth connect (ADR-386 D1), so a connected ChatGPT/Claude
 * appears as a named, revocable row. Human-member invite is still deferred (the
 * substrate re-key is its prerequisite, ADR-386 D6).
 *
 * ADR-338 management-plane idiom: legible + governable "who can touch this
 * workspace."
 */

import { useEffect, useState } from 'react';
import { Users, ShieldCheck, Bot, Plug, User, Cpu, Loader2, MoreHorizontal, ShieldMinus, Trash2, AlertTriangle, Link as LinkIcon, Plus } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { providerBrandIcon } from '@/lib/ai-providers/brand-icons';

type Member = Awaited<ReturnType<typeof api.workspace.getMembers>>['members'][number];

// The ADR-320 roots a member can be scoped to (the NARROW options). Operators
// don't think in path prefixes — these render with REGION_LABEL friendly names.
const NARROWABLE_REGIONS = ['operation/', 'agents/'] as const;

export type WorkspaceMembersVariant = 'full' | 'compact';

/**
 * The roster's presentation axis (ADR-431 §display). Principals split into two
 * KINDS the operator holds in their head — humans and external AI — because the
 * confusing screenshot was a flat list where "ChatGPT" sat between two people
 * with no signal that it is a categorically different principal. The split axis
 * is the grant `role`, never the wire transport (ADR-385: MCP is a transport an
 * AI chat AND an autonomous agent both arrive over; transport is row metadata,
 * not a grouping key).
 *
 * NOTE — what is NOT here: a member's in-chat model (Sonnet/Gemini via the
 * router, ADR-408 A2) is NOT a principal and never appears on this roster. It
 * writes as `member:{user} via {model}` under the MEMBER's grant (the member is
 * the principal, the model is the tool they hold). This roster is scoped to
 * principals only: humans, external LLMs reaching in over MCP, and (future,
 * ADR-382) Altitude-3 persona agents.
 */
const HUMAN_ROLES = ['owner', 'member'] as const;
const AI_ROLES = ['foreign-llm', 'a2a', 'platform', 'own-agent'] as const;

interface WorkspaceMembersCardProps {
  variant?: WorkspaceMembersVariant;
  className?: string;
  /** Optional override for the empty state (shown when the roster is empty). */
  emptyTitle?: string;
  emptyHint?: string;
}

// Role → presentation (icon + human label). The internal slugs are stable
// (GLOSSARY exceptions); these are the operator-facing names.
const ROLE_META: Record<string, { label: string; icon: typeof Users; tone: string }> = {
  owner: { label: 'Owner', icon: ShieldCheck, tone: 'text-emerald-600 dark:text-emerald-400' },
  member: { label: 'Member', icon: User, tone: 'text-blue-600 dark:text-blue-400' },
  'own-agent': { label: 'Agent', icon: Bot, tone: 'text-violet-600 dark:text-violet-400' },
  'foreign-llm': { label: 'External LLM', icon: Cpu, tone: 'text-amber-600 dark:text-amber-400' },
  platform: { label: 'Platform', icon: Plug, tone: 'text-cyan-600 dark:text-cyan-400' },
  a2a: { label: 'Agent (A2A)', icon: Bot, tone: 'text-violet-600 dark:text-violet-400' },
};

// Narrow-region root → operator-facing name for the NARROW dialog options.
// ADR-424: the roster displays operator ZONES (Documents/Downloads/System files,
// resolved backend-side into `write_zones`), never raw kernel roots. This map is
// now only the NARROW picker's option labels — the two regions an operator can
// grant a member (operation/ = the Documents home; agents/ = the agents home),
// named in the same operator vocabulary the Files tree uses.
const REGION_LABEL: Record<string, string> = {
  'operation/': 'Documents',
  'agents/': 'Agents',
};

function regionLabel(region: string): string {
  return REGION_LABEL[region] ?? REGION_LABEL[region.replace(/\/?$/, '/')] ?? region;
}

export function WorkspaceMembersCard({
  variant = 'full',
  className,
  emptyTitle,
  emptyHint,
}: WorkspaceMembersCardProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  // ADR-437 D5 — proactive seat awareness (Free = owner + 1 guest, ADR-429 §12.3c).
  const [seatInfo, setSeatInfo] = useState<{ human: number; included: number; available: boolean } | null>(null);
  // ADR-386 D2 — lifecycle verb state.
  const [menuFor, setMenuFor] = useState<string | null>(null);   // principal_id whose menu is open
  const [revokeTarget, setRevokeTarget] = useState<Member | null>(null);
  const [narrowTarget, setNarrowTarget] = useState<Member | null>(null);
  const [busy, setBusy] = useState(false);
  // ADR-404 step 5 — human-member invites (owner-only; API 403s otherwise).
  type Invite = Awaited<ReturnType<typeof api.workspace.listInvites>>['invites'][number];
  const [invites, setInvites] = useState<Invite[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [lastInviteLink, setLastInviteLink] = useState<string | null>(null);
  const [canInvite, setCanInvite] = useState(true); // false when the API 403s (non-owner)

  const refreshInvites = async () => {
    try {
      const res = await api.workspace.listInvites();
      setInvites(res.invites);
      setCanInvite(true);
    } catch {
      // 403 (member viewing) or transport failure — hide the invite affordance.
      setInvites([]);
      setCanInvite(false);
    }
  };

  const onInvite = async () => {
    const email = inviteEmail.trim();
    if (!email) return;
    setInviting(true);
    setInviteError(null);
    setLastInviteLink(null);
    try {
      const created = await api.workspace.inviteMember(email);
      setInviteEmail('');
      setLastInviteLink(created.invite_link ?? null);
      await refreshInvites();
    } catch (e) {
      const detail =
        e && typeof e === 'object' && 'data' in e &&
        typeof (e as { data?: { detail?: unknown } }).data?.detail === 'string'
          ? String((e as { data?: { detail?: unknown } }).data?.detail)
          : 'Could not send the invite.';
      setInviteError(detail);
    } finally {
      setInviting(false);
    }
  };

  const onRevokeInvite = async (id: string) => {
    try {
      await api.workspace.revokeInvite(id);
      await refreshInvites();
    } catch {
      // best-effort; list refresh shows truth
    }
  };

  const refresh = async () => {
    try {
      const res = await api.workspace.getMembers();
      setMembers(res.members);
      setSeatInfo({ human: res.human_seats, included: res.included_seats, available: res.seats_available });
    } catch {
      setMembers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.workspace.getMembers();
        if (!cancelled) {
          setMembers(res.members);
          setSeatInfo({ human: res.human_seats, included: res.included_seats, available: res.seats_available });
        }
      } catch {
        if (!cancelled) setMembers([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
      // Invite roster is owner-only; loaded separately so a member's 403
      // never blanks the members list.
      if (!cancelled) void refreshInvites();
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onRevoke = async (m: Member) => {
    setBusy(true);
    try {
      // ADR-431 — target the specific member's connection when a provider is
      // connected by several members (connected_by disambiguates the grant).
      await api.workspace.revokeMember(m.principal_id, m.connected_by);
      setRevokeTarget(null);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const onNarrow = async (m: Member, writeScopes: string[], readScopes: string[]) => {
    setBusy(true);
    try {
      // Two axes. Omit readScopes when it equals writeScopes (read ⊇ write, the
      // common case) so the backend applies its mirror default; pass it when the
      // operator moved the read axis independently.
      const sameAxes =
        readScopes.length === writeScopes.length &&
        readScopes.every((s) => writeScopes.includes(s));
      await api.workspace.narrowMember(m.principal_id, writeScopes, {
        readScopes: sameAxes ? undefined : readScopes,
        connectedBy: m.connected_by,
      });
      setNarrowTarget(null);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  // ADR-431 §display — split the ONE roster fetch into the two principal KINDS
  // (humans / external AI). Not a data fork (DP29): one fetch, partitioned for
  // legibility. A member's in-chat model is not here at all (it's not a
  // principal), so the two partitions are exhaustive over the roster.
  const humans = members.filter((m) => (HUMAN_ROLES as readonly string[]).includes(m.role));
  const ais = members.filter((m) => (AI_ROLES as readonly string[]).includes(m.role));

  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 rounded-lg border border-border px-4 py-6 text-sm text-muted-foreground', className)}>
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading members…
      </div>
    );
  }

  const renderEmptyState = (title?: string, hint?: string) => (
    <div className="rounded-lg border border-dashed border-border/60 px-4 py-6 text-center">
      <Users className="mx-auto h-5 w-5 text-muted-foreground/50" />
      <p className="mt-2 text-sm font-medium text-foreground/80">{title ?? 'No members yet'}</p>
      <p className="mt-1 text-xs text-muted-foreground/70 max-w-sm mx-auto">
        {hint ?? 'This workspace has no principal grants. Once you author substrate, you become its owner.'}
      </p>
    </div>
  );

  // One row renderer for both partitions — the governance verbs (narrow /
  // revoke) ride along unchanged.
  const renderMemberList = (list: Member[]) => (
    <ul className="divide-y divide-border rounded-lg border border-border">
      {list.map((m) => {
        const meta = ROLE_META[m.role] ?? { label: m.role, icon: Users, tone: 'text-muted-foreground' };
        const Icon = meta.icon;
        const name = m.label ?? m.principal_id;
        // ADR-386 D4 — the owner grant is immutable from this surface: no verbs.
        const governable = m.role !== 'owner';
        // ADR-431 §display — the one-line "what kind of principal is this" hint
        // that carries the conceptual framing. For an external LLM it names the
        // distinguishing fact: it reaches in autonomously over MCP and writes
        // as ITSELF — categorically unlike a member's in-chat model (which
        // writes as the member). Kept to a single short clause; no new data.
        const kindHint =
          m.role === 'foreign-llm'
            ? 'Connects over MCP · writes as itself'
            : m.role === 'a2a'
            ? 'Agent-to-agent caller · writes as itself'
            : m.role === 'platform'
            ? 'Platform integration · writes as itself'
            : m.role === 'own-agent'
            ? 'Workspace agent · writes as itself'
            : null;
        // ADR-431 D3 — WHO authorized this AI connection ("whose ChatGPT").
        // Resolves the operator's "whose?" question directly. "You" when the
        // viewer authorized it, else the member's email. Rendered as its own
        // prominent attribution line (not buried in the kind hint).
        const isExternalAI = m.role === 'foreign-llm' || m.role === 'a2a' || m.role === 'platform';
        const connectedByName = m.connected_by_is_you ? 'You' : (m.connected_by_label ?? null);
        // ADR-424 — show OPERATOR ZONES (Documents/Downloads/System files), NOT
        // the raw kernel roots. write_zones is the backend's operator projection.
        const zones = m.write_zones ?? [];
        return (
          <li key={`${m.principal_id}-${m.role}`} className="flex items-start gap-3 px-4 py-3">
            {/* ADR-431 §display — external LLMs render their PROVIDER brand mark
                (keyed on principal_id = the host-id) so ChatGPT ≠ Claude at a
                glance; humans + own-agent keep the role's lucide glyph. */}
            <div className={cn('mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted', meta.tone)}>
              {isExternalAI ? providerBrandIcon(m.principal_id) : <Icon className={cn('h-4 w-4', meta.tone)} />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium text-foreground">{name}</span>
                <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                  {meta.label}
                </span>
              </div>
              {/* ADR-431 D3 — WHO authorized this AI connection, first-class:
                  a distinct, legible line (not a dim tail clause). */}
              {isExternalAI && connectedByName && (
                <div className="mt-1 flex items-center gap-1.5 text-[11px]">
                  <LinkIcon className="h-3 w-3 text-muted-foreground/60" />
                  <span className="text-muted-foreground/70">Connected by</span>
                  <span className="font-medium text-foreground/80">{connectedByName}</span>
                </div>
              )}
              {kindHint && (
                <p className="mt-0.5 text-[11px] text-muted-foreground/50">{kindHint}</p>
              )}
              {/* Powerbox (2026-07-10): TWO AXES. The chips are the WRITE reach
                  (the operator zones); a read-only badge shows when the read axis
                  is broader than write (an auditor: reads a folder, writes none).
                  'none' write with any read = read-only; 'none' both = no access. */}
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] text-muted-foreground/70">
                  {m.write_state === 'scoped' ? 'Can write (narrowed)' : m.write_state === 'none' ? 'Write' : 'Can write'}:
                </span>
                {m.write_state === 'none' ? (
                  m.read_state === 'none' ? (
                    <span className="text-[11px] font-medium text-amber-600 dark:text-amber-400">
                      nothing (access removed)
                    </span>
                  ) : (
                    <span className="rounded bg-blue-500/10 px-1.5 py-0.5 text-[11px] font-medium text-blue-600 dark:text-blue-400">
                      read-only
                    </span>
                  )
                ) : zones.length === 0 ? (
                  <span className="text-[11px] text-muted-foreground/60 italic">nothing</span>
                ) : (
                  zones.map((zone) => (
                    <span
                      key={zone}
                      className="rounded border border-border/60 px-1.5 py-0.5 text-[11px] text-foreground/70"
                    >
                      {zone}
                    </span>
                  ))
                )}
                {/* When read is scoped BROADER than write (both scoped but read has
                    more), hint that reads reach further. */}
                {m.write_state !== 'none' && m.read_state === 'scoped' &&
                  (m.read_scopes?.length ?? 0) > (m.write_regions?.length ?? 0) && (
                    <span className="rounded bg-blue-500/10 px-1.5 py-0.5 text-[10px] text-blue-600 dark:text-blue-400">
                      +read
                    </span>
                  )}
              </div>
            </div>
            {governable && (
              <div className="relative shrink-0">
                <button
                  type="button"
                  aria-label={`Manage ${name}`}
                  onClick={() => setMenuFor(menuFor === m.principal_id ? null : m.principal_id)}
                  className="rounded p-1 text-muted-foreground/60 hover:bg-muted hover:text-foreground"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>
                {menuFor === m.principal_id && (
                  <>
                    {/* click-away */}
                    <div className="fixed inset-0 z-10" onClick={() => setMenuFor(null)} />
                    <div className="absolute right-0 z-20 mt-1 w-40 overflow-hidden rounded-md border border-border bg-popover shadow-md">
                      <button
                        type="button"
                        onClick={() => { setMenuFor(null); setNarrowTarget(m); }}
                        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted"
                      >
                        <ShieldMinus className="h-3.5 w-3.5 text-muted-foreground" />
                        Narrow access
                      </button>
                      <button
                        type="button"
                        onClick={() => { setMenuFor(null); setRevokeTarget(m); }}
                        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Revoke…
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );

  if (members.length === 0) {
    return <div className={className}>{renderEmptyState(emptyTitle, emptyHint)}</div>;
  }

  return (
    <div className={cn('space-y-6', className)}>
      {variant === 'full' && (
        <p className="text-sm text-muted-foreground">
          Everyone — and everything — that can write to this workspace. People are the humans on
          the workspace; <span className="font-medium text-foreground/80">AI connections</span> are
          external LLMs that reach in over MCP and write as themselves. (A member&rsquo;s in-chat
          model isn&rsquo;t here — it writes as the member, not as its own principal.) Narrow or
          revoke any principal&rsquo;s access.
        </p>
      )}

      {/* ADR-404 step 5 — invite a human member (owner-only; hidden on 403). */}
      {variant === 'full' && canInvite && (
        <div className="rounded-lg border border-border p-3">
          {/* ADR-437 D5 — proactive seat awareness AT the invite affordance, so
              the Free = owner + 1 guest boundary (ADR-429 §12.3c) is visible
              before it's hit as a surprise 402. */}
          {seatInfo && seatInfo.included > 0 && (
            <p className="mb-2 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">
                {seatInfo.human} of {seatInfo.included} {seatInfo.included === 1 ? 'seat' : 'seats'} used
              </span>
              {!seatInfo.available && (
                <span className="text-amber-600 dark:text-amber-400">
                  {' '}· seat limit reached — upgrade to invite more people
                </span>
              )}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && seatInfo?.available !== false) void onInvite(); }}
              placeholder="teammate@company.com"
              className="min-w-0 flex-1 rounded-md border border-border/60 bg-background px-2.5 py-1.5 text-sm"
              aria-label="Invite email"
            />
            <button
              onClick={() => void onInvite()}
              disabled={inviting || !inviteEmail.trim() || seatInfo?.available === false}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
            >
              {inviting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Invite member
            </button>
          </div>
          <p className="mt-1.5 text-xs text-muted-foreground">
            Members join this workspace with write access to Operation and Agents —
            every change they make is attributed to them. Narrow or revoke any time.
          </p>
          {inviteError && <p className="mt-1.5 text-xs text-destructive">{inviteError}</p>}
          {lastInviteLink && (
            <p className="mt-1.5 break-all text-xs text-muted-foreground">
              Invite sent. Link (share directly if the email doesn&rsquo;t arrive):{' '}
              <span className="font-mono text-foreground/80">{lastInviteLink}</span>
            </p>
          )}
          {invites.length > 0 && (
            <ul className="mt-3 space-y-1.5 border-t border-border/60 pt-2">
              {invites.map((inv) => (
                <li key={inv.id} className="flex items-center justify-between gap-2 text-xs">
                  <span className="truncate text-muted-foreground">
                    {inv.email} <span className="text-muted-foreground/60">· pending</span>
                  </span>
                  <button
                    onClick={() => void onRevokeInvite(inv.id)}
                    className="shrink-0 text-muted-foreground/70 underline-offset-2 hover:text-destructive hover:underline"
                  >
                    Revoke
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ADR-431 §display — two partitions of the ONE roster fetch: People
          (humans) and AI connections (external LLMs). The AI section only
          appears once at least one AI principal exists, so a cold-start
          workspace (owner only) sees a clean People list, not an empty AI box. */}
      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          People
        </h3>
        {humans.length === 0 ? renderEmptyState('No people yet') : renderMemberList(humans)}
      </section>

      {ais.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            AI connections
          </h3>
          {renderMemberList(ais)}
        </section>
      )}

      {/* ADR-386 D2/D3 — REVOKE = full eviction. The modal emphasizes the weight:
          irreversible-feeling, names the consequence BEFORE the click. */}
      {revokeTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => !busy && setRevokeTarget(null)}>
          <div className="w-full max-w-md rounded-lg border border-border bg-background p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-foreground">
                  Revoke {revokeTarget.label ?? revokeTarget.principal_id}?
                </h3>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  This is a full eviction. <span className="font-medium text-foreground/90">{revokeTarget.label ?? 'This principal'}</span> loses
                  all access immediately, its connection tokens are deleted, and it must
                  re-authorize from scratch to return. This cannot be undone from here.
                </p>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => setRevokeTarget(null)}
                className="rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-muted disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => onRevoke(revokeTarget)}
                className="inline-flex items-center gap-1.5 rounded-md bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
              >
                {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Revoke &amp; disconnect
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ADR-386 D2 — NARROW: tighten the member's write-region set (lightweight,
          token untouched). Distinct in weight from Revoke. */}
      {narrowTarget && (
        <NarrowDialog
          member={narrowTarget}
          busy={busy}
          onCancel={() => setNarrowTarget(null)}
          onConfirm={(write, read) => onNarrow(narrowTarget, write, read)}
        />
      )}
    </div>
  );
}

// The three access levels an operator assigns per path (powerbox two-axis).
// 'none' = the path is not in either scope; 'read' = read-only (read scope only);
// 'write' = read + write (in both scopes — read ⊇ write, the norm).
type AccessLevel = 'none' | 'read' | 'write';

/** A path the operator is scoping, with its level. Paths are prefixes at
 *  arbitrary depth ('operation/', 'operation/marketing/', 'operation/x.md'). */
interface ScopeRow {
  path: string;
  level: AccessLevel;
}

function normalizePrefix(p: string): string {
  const t = p.trim().replace(/^\/+/, '').replace(/^workspace\//, '');
  return t;
}

/**
 * NarrowDialog — set a member's READ + WRITE scope, at arbitrary path depth
 * (ADR-386 D2; the powerbox, 2026-07-10). TWO INDEPENDENT AXES: each path gets
 * a level — No access / Read only / Read & write — so a read-only auditor
 * (read a folder, write nothing) is expressible, and paths can be any depth
 * ('operation/marketing/' or a single file), not just top-level zones. An empty
 * result on an axis is a deliberate DENY-ALL for that axis. (Full eviction —
 * disconnect + token delete — is the separate Revoke modal.)
 */
function NarrowDialog({
  member,
  busy,
  onCancel,
  onConfirm,
}: {
  member: Member;
  busy: boolean;
  onCancel: () => void;
  onConfirm: (writeScopes: string[], readScopes: string[]) => void;
}) {
  // Seed the rows from the member's current two-axis grant. Union the read +
  // write prefixes; a path in write_regions is 'write', a read-only path is
  // 'read'. The quick-pick zones (Documents/Agents) seed as rows too, so the
  // common case is one click, and deeper paths are added by hand.
  const seedRows = (): ScopeRow[] => {
    const write = new Set(member.write_regions.map(normalizePrefix).filter(Boolean));
    const read = new Set((member.read_scopes ?? []).map(normalizePrefix).filter(Boolean));
    // A fresh, unconfigured member: default to Documents = read & write.
    if (member.write_state === 'all' && member.read_state === 'all') {
      return [{ path: 'operation/', level: 'write' }];
    }
    const paths = Array.from(new Set<string>([...Array.from(write), ...Array.from(read)]));
    const rows: ScopeRow[] = [];
    for (const p of paths) {
      const level: AccessLevel = write.has(p) ? 'write' : read.has(p) ? 'read' : 'none';
      if (level !== 'none') rows.push({ path: p, level });
    }
    return rows;
  };

  const [rows, setRows] = useState<ScopeRow[]>(seedRows);
  const [newPath, setNewPath] = useState('');

  const setLevel = (path: string, level: AccessLevel) =>
    setRows((rs) =>
      level === 'none'
        ? rs.filter((r) => r.path !== path)
        : rs.map((r) => (r.path === path ? { ...r, level } : r)),
    );

  const addPath = () => {
    const p = normalizePrefix(newPath);
    if (!p || rows.some((r) => r.path === p)) return;
    setRows((rs) => [...rs, { path: p, level: 'write' }]);
    setNewPath('');
  };

  const addZone = (region: string) => {
    const p = normalizePrefix(region);
    if (rows.some((r) => r.path === p)) return;
    setRows((rs) => [...rs, { path: p, level: 'write' }]);
  };

  // Derive the two axes: write = 'write' rows; read = 'write' ∪ 'read' rows
  // (read ⊇ write). Empty axis → deny-all for that axis.
  const writeScopes = rows.filter((r) => r.level === 'write').map((r) => r.path);
  const readScopes = rows.filter((r) => r.level !== 'none').map((r) => r.path);
  const denyAllWrite = writeScopes.length === 0;
  const denyAllBoth = readScopes.length === 0;

  const zoneRows = rows.map((r) => r.path);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => !busy && onCancel()}>
      <div className="w-full max-w-lg rounded-lg border border-border bg-background p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-foreground">
          Set {member.label ?? member.principal_id}&rsquo;s access
        </h3>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Grant read or read &amp; write on any folder or file. Paths can be as
          deep as you like. Anything not listed is hidden and denied — the member
          stays connected either way.
        </p>

        {/* Quick-pick zones — one click to add a top-level home as a row. */}
        <div className="mt-4 flex flex-wrap gap-1.5">
          {NARROWABLE_REGIONS.filter((rg) => !zoneRows.includes(normalizePrefix(rg))).map((region) => (
            <button
              key={region}
              type="button"
              onClick={() => addZone(region)}
              className="inline-flex items-center gap-1 rounded-md border border-dashed border-border px-2 py-1 text-[12px] text-muted-foreground hover:bg-muted/50"
            >
              <Plus className="h-3 w-3" /> {regionLabel(region)}
            </button>
          ))}
        </div>

        {/* The scope rows — each path with its access level. */}
        <div className="mt-3 space-y-1.5">
          {rows.length === 0 && (
            <p className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[13px] text-amber-700 dark:text-amber-400">
              No paths — this removes all access. {member.label ?? 'The principal'} stays
              connected but can read and write nothing. (To disconnect entirely, use Revoke.)
            </p>
          )}
          {rows.map((r) => (
            <div key={r.path} className="flex items-center gap-2 rounded-md border border-border/60 px-3 py-2">
              <code className="min-w-0 flex-1 truncate text-[13px] text-foreground/80" title={r.path}>
                {r.path}
              </code>
              <div className="flex shrink-0 overflow-hidden rounded border border-border text-[11px]">
                {(['none', 'read', 'write'] as AccessLevel[]).map((lvl) => (
                  <button
                    key={lvl}
                    type="button"
                    onClick={() => setLevel(r.path, lvl)}
                    className={cn(
                      'px-2 py-1 capitalize',
                      r.level === lvl
                        ? lvl === 'none'
                          ? 'bg-amber-600 text-white'
                          : 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-muted/60',
                    )}
                  >
                    {lvl === 'none' ? 'No access' : lvl === 'read' ? 'Read' : 'Read+Write'}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Add a deeper path by hand (object-granularity). */}
        <div className="mt-2 flex items-center gap-2">
          <input
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addPath())}
            placeholder="e.g. operation/marketing/ or operation/reports/q3.md"
            className="min-w-0 flex-1 rounded-md border border-input bg-background px-2.5 py-1.5 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <button
            type="button"
            onClick={addPath}
            disabled={!normalizePrefix(newPath)}
            className="shrink-0 rounded-md border border-border px-2.5 py-1.5 text-[12px] font-medium hover:bg-muted disabled:opacity-40"
          >
            Add path
          </button>
        </div>

        {/* Honest summary of what the two axes resolve to. */}
        <p className="mt-3 text-[11px] text-muted-foreground">
          {denyAllBoth
            ? 'Read: nothing · Write: nothing'
            : `Read: ${readScopes.length} path${readScopes.length === 1 ? '' : 's'}` +
              ` · Write: ${denyAllWrite ? 'nothing (read-only)' : `${writeScopes.length} path${writeScopes.length === 1 ? '' : 's'}`}`}
        </p>

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onCancel}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onConfirm(writeScopes, readScopes)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50',
              denyAllBoth
                ? 'bg-amber-600 text-white hover:bg-amber-600/90'
                : 'bg-primary text-primary-foreground hover:bg-primary/90',
            )}
          >
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {denyAllBoth ? 'Remove all access' : 'Apply'}
          </button>
        </div>
      </div>
    </div>
  );
}
