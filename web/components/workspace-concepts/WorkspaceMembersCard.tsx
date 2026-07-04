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
import { Users, ShieldCheck, Bot, Plug, User, Cpu, Loader2, MoreHorizontal, ShieldMinus, Trash2, AlertTriangle } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type Member = Awaited<ReturnType<typeof api.workspace.getMembers>>['members'][number];

// The ADR-320 roots a member can be scoped to (the NARROW options). Operators
// don't think in path prefixes — these render with REGION_LABEL friendly names.
const NARROWABLE_REGIONS = ['operation/', 'agents/'] as const;

export type WorkspaceMembersVariant = 'full' | 'compact';

interface WorkspaceMembersCardProps {
  variant?: WorkspaceMembersVariant;
  className?: string;
  /**
   * ADR-385 D3 — restrict the rendered roster to these principal roles. When
   * omitted, all roles render (the full Workspace-Settings → Access roster).
   * The Channels → AI Connections pane (slug `external-agents`) passes
   * `['foreign-llm', 'a2a', 'platform']` to show only the external/automation
   * principals (MCP LLMs, agent-to-agent callers, platform writers) — a second
   * VIEW of the one principal_grants substrate, not a parallel source (DP29).
   */
  roleFilter?: string[];
  /** Optional override for the empty state (shown when the filtered roster is empty). */
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

// Write-region root → a short operator-facing name. The roots are the ADR-320
// semantic classes; operators don't think in path prefixes.
const REGION_LABEL: Record<string, string> = {
  'governance/': 'Governance',
  'constitution/': 'Constitution',
  'persona/': 'Persona',
  'operation/': 'Operation',
  'contract/': 'Contract',
  'system/': 'System',
  'agents/': 'Agents',
};

function regionLabel(region: string): string {
  return REGION_LABEL[region] ?? REGION_LABEL[region.replace(/\/?$/, '/')] ?? region;
}

export function WorkspaceMembersCard({
  variant = 'full',
  className,
  roleFilter,
  emptyTitle,
  emptyHint,
}: WorkspaceMembersCardProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
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
        if (!cancelled) setMembers(res.members);
      } catch {
        if (!cancelled) setMembers([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
      // Invite roster is owner-only; loaded separately so a member's 403
      // never blanks the members list. Only on the full (Access) roster.
      if (!cancelled && !roleFilter) void refreshInvites();
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onRevoke = async (m: Member) => {
    setBusy(true);
    try {
      await api.workspace.revokeMember(m.principal_id);
      setRevokeTarget(null);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const onNarrow = async (m: Member, scopes: string[]) => {
    setBusy(true);
    try {
      await api.workspace.narrowMember(m.principal_id, scopes);
      setNarrowTarget(null);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  // ADR-385 D3 — one substrate, two views: filter the rendered roster by role
  // without forking the data source.
  const visible = roleFilter ? members.filter((m) => roleFilter.includes(m.role)) : members;

  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 rounded-lg border border-border px-4 py-6 text-sm text-muted-foreground', className)}>
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading members…
      </div>
    );
  }

  if (visible.length === 0) {
    return (
      <div className={cn('rounded-lg border border-dashed border-border/60 px-4 py-6 text-center', className)}>
        <Users className="mx-auto h-5 w-5 text-muted-foreground/50" />
        <p className="mt-2 text-sm font-medium text-foreground/80">{emptyTitle ?? 'No members yet'}</p>
        <p className="mt-1 text-xs text-muted-foreground/70 max-w-sm mx-auto">
          {emptyHint ?? 'This workspace has no principal grants. Once you author substrate, you become its owner.'}
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {variant === 'full' && (
        roleFilter ? (
          <p className="text-sm text-muted-foreground">
            External LLMs, agent-to-agent callers, and platforms that reach into this workspace —
            each connects as a <span className="font-medium text-foreground/80">principal</span>,
            attributes its writes as itself, and is authorized to a specific region of the substrate.
            Granting and scoping their access is coming soon.
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">
            Everyone — and everything — that can write to this workspace. In this model an MCP
            connection from an external LLM is a <span className="font-medium text-foreground/80">member</span>:
            it attributes its writes as itself and is authorized to a specific region of the substrate.
            You can narrow a member&rsquo;s access or revoke it.
          </p>
        )
      )}

      {/* ADR-404 step 5 — invite a human member (owner-only; hidden on 403). */}
      {variant === 'full' && !roleFilter && canInvite && (
        <div className="rounded-lg border border-border p-3">
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') void onInvite(); }}
              placeholder="teammate@company.com"
              className="min-w-0 flex-1 rounded-md border border-border/60 bg-background px-2.5 py-1.5 text-sm"
              aria-label="Invite email"
            />
            <button
              onClick={() => void onInvite()}
              disabled={inviting || !inviteEmail.trim()}
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

      <ul className="divide-y divide-border rounded-lg border border-border">
        {visible.map((m) => {
          const meta = ROLE_META[m.role] ?? { label: m.role, icon: Users, tone: 'text-muted-foreground' };
          const Icon = meta.icon;
          const name = m.label ?? m.principal_id;
          // ADR-386 D4 — the owner grant is immutable from this surface: no verbs.
          const governable = m.role !== 'owner';
          return (
            <li key={`${m.principal_id}-${m.role}`} className="flex items-start gap-3 px-4 py-3">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
                <Icon className={cn('h-4 w-4', meta.tone)} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium text-foreground">{name}</span>
                  <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                    {meta.label}
                  </span>
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] text-muted-foreground/70">
                    {m.scopes_explicit ? 'Can write' : 'Can write (default)'}:
                  </span>
                  {m.write_regions.length === 0 ? (
                    <span className="text-[11px] text-muted-foreground/60 italic">nothing</span>
                  ) : (
                    m.write_regions.map((region) => (
                      <span
                        key={region}
                        className="rounded border border-border/60 px-1.5 py-0.5 text-[11px] text-foreground/70"
                      >
                        {regionLabel(region)}
                      </span>
                    ))
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
          onConfirm={(scopes) => onNarrow(narrowTarget, scopes)}
        />
      )}
    </div>
  );
}

/**
 * NarrowDialog — pick the write-regions a member is allowed to author (ADR-386
 * D2). Authz-only; lightweight vs the Revoke eviction modal.
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
  onConfirm: (scopes: string[]) => void;
}) {
  // Seed from the member's current explicit scopes (if narrowed already),
  // else default to operation/ only (the tightest sensible floor).
  const [selected, setSelected] = useState<string[]>(
    member.scopes_explicit && member.write_regions.length
      ? member.write_regions.map((r) => (r.endsWith('/') ? r : `${r}/`))
      : ['operation/'],
  );
  const toggle = (region: string) =>
    setSelected((s) => (s.includes(region) ? s.filter((x) => x !== region) : [...s, region]));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => !busy && onCancel()}>
      <div className="w-full max-w-md rounded-lg border border-border bg-background p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-foreground">
          Narrow {member.label ?? member.principal_id}&rsquo;s access
        </h3>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Choose the regions this principal may write. It stays connected and can still read;
          writes outside the selected regions are denied.
        </p>
        <div className="mt-4 space-y-1.5">
          {NARROWABLE_REGIONS.map((region) => (
            <label key={region} className="flex items-center gap-2 rounded-md border border-border/60 px-3 py-2 text-sm hover:bg-muted/50">
              <input
                type="checkbox"
                checked={selected.includes(region)}
                onChange={() => toggle(region)}
                className="h-4 w-4"
              />
              {regionLabel(region)}
            </label>
          ))}
        </div>
        <div className="mt-5 flex justify-end gap-2">
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
            disabled={busy || selected.length === 0}
            onClick={() => onConfirm(selected)}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}
