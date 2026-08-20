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
import { Users, ShieldCheck, Bot, User, Cpu, Loader2, MoreHorizontal, ShieldMinus, Trash2, AlertTriangle, Link as LinkIcon, Plus, Wallet } from 'lucide-react';
import { api, getActiveWorkspaceId } from '@/lib/api/client';
import { useWorkspaceMemberships } from '@/lib/workspace/viewer';
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
// ADR-517 D6 — `viewer` is a first-class human role (role-honest grants): it
// renders in the roster (an invisible principal is an ungovernable one) but is
// NOT a billing seat (HUMAN_SEAT_ROLES stays owner|member, server-side).
const HUMAN_ROLES = ['owner', 'member', 'viewer'] as const;
// ADR-497 — the DISPLAY vocabulary carries only roles something can actually
// create. `foreign-llm` is minted by the MCP OAuth flow
// (`oauth_provider.py::_ensure_foreign_llm_grant`); `own-agent` by program
// activation (`programs.py::mint_hire_grant`, ADR-414 D5 program-as-hire —
// reachable, zero live rows). `a2a` and `platform` had NO creation path
// anywhere in the codebase — their only trace was presentation metadata here,
// describing principals that cannot exist. Reserved seats (ADR-382 / ADR-401
// D1) stay in the DB CHECK constraint and in the eviction sweep
// (`principal_grants.py:549`, which must stay broad so a row would still be
// cleaned up) — a reserved seat is a substrate fact, not a rendered one.
const AI_ROLES = ['foreign-llm', 'own-agent'] as const;

/**
 * WHOSE principals the roster renders (ADR-496 D1).
 *
 * - `workspace` — every principal in the commons. The governance surface.
 * - `mine`      — only the principals the VIEWER authorized
 *                 (`connected_by_is_you`). The account-door mirror: a member
 *                 asking "what have I connected?" without opening a surface
 *                 whose job is governing other people.
 *
 * This is a FILTER on the one roster fetch, never a second fetch or a second
 * component (DP29 "mirror once"): the same rows, the same row renderer, the
 * same brand marks and zone chips — so the two surfaces cannot drift into two
 * visual languages for one fact.
 */
export type WorkspaceMembersScope = 'workspace' | 'mine';

interface WorkspaceMembersCardProps {
  variant?: WorkspaceMembersVariant;
  /** Whose principals to show. Defaults to the whole commons. */
  scope?: WorkspaceMembersScope;
  /** Opt OUT of the governance verbs (narrow / revoke). The account-door mirror
   *  sets this: governance stays SINGULAR on the workspace door, which this
   *  surface links across to instead of duplicating. */
  readOnly?: boolean;
  className?: string;
  /** Optional override for the empty state (shown when the roster is empty). */
  emptyTitle?: string;
  emptyHint?: string;
  /** Rendered after the roster sections (e.g. the mirror's cross-link). */
  footer?: React.ReactNode;
}

// Role → presentation (icon + human label). The internal slugs are stable
// (GLOSSARY exceptions); these are the operator-facing names.
const ROLE_META: Record<string, { label: string; icon: typeof Users; tone: string }> = {
  owner: { label: 'Owner', icon: ShieldCheck, tone: 'text-emerald-600 dark:text-emerald-400' },
  member: { label: 'Member', icon: User, tone: 'text-blue-600 dark:text-blue-400' },
  viewer: { label: 'Viewer', icon: User, tone: 'text-muted-foreground' },
  'own-agent': { label: 'Agent', icon: Bot, tone: 'text-violet-600 dark:text-violet-400' },
  'foreign-llm': { label: 'External LLM', icon: Cpu, tone: 'text-amber-600 dark:text-amber-400' },
};

// ADR-563 — the CONNECTION's verb tier, as one operator-facing label.
//
// A different axis from the write/read REGIONS this pane already shows: those
// answer "where may this principal reach", this answers "what may its token do
// there". Both are real and neither implies the other — a connector narrowed to
// Documents can still hold a token that deletes and shares within it.
//
// The tiers are additive (files:read ⊂ files:write ⊂ files:share) and `read` is
// the LEGACY full-access grant every pre-ADR-563 token carries, so it is named
// plainly rather than shown as if it were a narrow scope — that silence is the
// exact thing ADR-563 exists to end. Order matters: check widest first.
function describeConnectionTier(
  scopes: string[] | null,
  legacyFull: boolean,
): { label: string; tone: string } | null {
  if (legacyFull) {
    return {
      label: 'Everything (full access)',
      tone: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    };
  }
  if (!scopes || scopes.length === 0) return null;
  if (scopes.includes('files:share')) {
    return {
      label: 'Read, write & share',
      tone: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    };
  }
  if (scopes.includes('files:write')) {
    return {
      label: 'Read & write',
      tone: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    };
  }
  if (scopes.includes('files:read')) {
    return {
      label: 'Read only',
      tone: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    };
  }
  // An unrecognized scope is shown as unknown rather than guessed at — never
  // imply a capability this build does not understand.
  return { label: 'Unrecognized permission', tone: 'bg-muted text-muted-foreground' };
}

// ADR-550 — the viewer's own standing, said in the second person. Separate from
// ROLE_META (which labels OTHER people's rows) because the sentence differs:
// a row says what someone IS, the header says what YOU can do. Same three human
// roles, so the two maps stay in step by construction — a role added to
// HUMAN_ROLES without an entry here is a type error.
const VIEWER_ROLE_LABEL: Record<'owner' | 'member' | 'viewer', string> = {
  owner: 'owner',
  member: 'member',
  viewer: 'viewer',
};

// What the role actually MEANS in affordance terms — the honest summary of the
// grant, matching what the server enforces (owner-only invite/narrow/revoke/cap
// per routes/workspace.py::_require_owner_workspace; a member writes Documents
// but not System files; a viewer reads).
const VIEWER_ROLE_HINT: Record<'owner' | 'member' | 'viewer', string> = {
  owner:
    'You can invite people, change what everyone can reach, and manage billing.',
  member:
    'You can read and write this workspace’s documents. Only the owner can invite people or change access.',
  viewer:
    'You can read this workspace. You can’t write to it, invite people, or change access.',
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

/** The server's own refusal text, or `fallback` when it carried none.
 *
 * The reason is already operator-grade ("Only the workspace owner can change a
 * member's access", "narrow cannot widen the write axis …"), so prefer it over
 * anything invented client-side.
 *
 * TWO WIRE SHAPES, and reading only one is how this silently degrades: raw
 * FastAPI raises surface as `{detail}`, while anything through the envelope
 * middleware arrives as `{error: {code, message}}`. The governance verbs use
 * the SECOND — verified by probing /narrow as a member (403
 * `{"error":{"code":"forbidden","message":"Only the workspace owner …"}}`).
 * A `detail`-only reader compiles, ships, and quietly shows the generic
 * fallback forever. */
function serverDetail(e: unknown, fallback: string): string {
  const data =
    e && typeof e === 'object' && 'data' in e
      ? (e as { data?: unknown }).data
      : undefined;
  if (data && typeof data === 'object') {
    const d = data as { detail?: unknown; error?: { message?: unknown } };
    const detail = d.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    const message = d.error?.message;
    if (typeof message === 'string' && message.trim()) return message;
  }
  return fallback;
}

export function WorkspaceMembersCard({
  variant = 'full',
  scope = 'workspace',
  readOnly = false,
  className,
  emptyTitle,
  emptyHint,
  footer,
}: WorkspaceMembersCardProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  // ADR-550 — the workspace's NAME for the header. Module-cached and already
  // fetched once per page life by the shell, so this adds no request.
  const { memberships } = useWorkspaceMemberships();
  // ADR-445 §6 — proactive seat awareness (Free = solo; the 2nd human is paid).
  const [seatInfo, setSeatInfo] = useState<{ human: number; included: number; available: boolean } | null>(null);
  // ADR-386 D2 — lifecycle verb state.
  const [menuFor, setMenuFor] = useState<string | null>(null);   // principal_id whose menu is open
  const [revokeTarget, setRevokeTarget] = useState<Member | null>(null);
  const [narrowTarget, setNarrowTarget] = useState<Member | null>(null);
  // ADR-445 §7 Phase 4 — the per-member spend-cap dialog target.
  const [capTarget, setCapTarget] = useState<Member | null>(null);
  const [busy, setBusy] = useState(false);
  // The server's refusal, in its own words. The governance verbs (narrow /
  // revoke / cap) are owner-only and `narrow` additionally refuses a WIDENING
  // change; both arrive as a 403 whose `detail` already explains why. Without
  // somewhere to put it the throw was swallowed and the dialog just sat there.
  const [governError, setGovernError] = useState<string | null>(null);
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
    } catch (e) {
      // ONLY a 403 means "this viewer is not the owner" — hide the affordance.
      // A transport blip must NOT be read as a loss of authority: doing so
      // blanked the roster right after a successful invite, so the owner saw an
      // empty list and reasonably concluded the invite had failed (2026-07-31
      // click-pass F2). Keep the last known roster and stay visible instead.
      const status =
        e && typeof e === 'object' && 'status' in e
          ? (e as { status?: number }).status
          : undefined;
      if (status === 403) {
        setInvites([]);
        setCanInvite(false);
      }
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
      setInviteError(serverDetail(e, 'Could not send the invite.'));
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
    setGovernError(null);
    try {
      // ADR-431 — target the specific member's connection when a provider is
      // connected by several members (connected_by disambiguates the grant).
      await api.workspace.revokeMember(m.principal_id, m.connected_by);
      setRevokeTarget(null);
      await refresh();
    } catch (e) {
      setGovernError(serverDetail(e, 'Could not revoke this member.'));
    } finally {
      setBusy(false);
    }
  };

  const onNarrow = async (m: Member, writeScopes: string[], readScopes: string[]) => {
    setBusy(true);
    setGovernError(null);
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
    } catch (e) {
      // The server refuses this for two good reasons — the caller is not the
      // owner, or the change would WIDEN rather than narrow. Both arrive as a
      // 403 carrying the reason in `detail`. Before this, the throw was
      // swallowed by a bare try/finally and the dialog just sat there
      // (2026-07-31 click-pass F4): a correct refusal the operator could not see.
      setGovernError(serverDetail(e, 'Could not change this member’s access.'));
    } finally {
      setBusy(false);
    }
  };

  // ADR-445 §7 Phase 4 — owner sets/clears a member's spend cap on the shared pool.
  const onCap = async (m: Member, capUsd: number | null) => {
    setBusy(true);
    setGovernError(null);
    try {
      await api.workspace.capMember(m.principal_id, capUsd);
      setCapTarget(null);
      await refresh();
    } catch (e) {
      setGovernError(serverDetail(e, 'Could not set this member’s spend cap.'));
    } finally {
      setBusy(false);
    }
  };

  // ADR-431 §display — split the ONE roster fetch into the two principal KINDS
  // (humans / external AI). Not a data fork (DP29): one fetch, partitioned for
  // legibility. A member's in-chat model is not here at all (it's not a
  // principal), so the two partitions are exhaustive over the roster.
  // ADR-496 D1 — the scope filter. `mine` keeps only the principals the VIEWER
  // authorized, using the attributed fact ADR-431 D3 already serves
  // (`connected_by_is_you`). A human's own row is theirs by definition; an AI
  // connection's is decided by who ran its OAuth flow. Applied BEFORE the
  // kind-partition so both sections narrow together.
  const scoped =
    scope === 'mine'
      ? members.filter((m) =>
          (AI_ROLES as readonly string[]).includes(m.role)
            ? m.connected_by_is_you === true
            : false,
        )
      : members;
  const humans = scoped.filter((m) => (HUMAN_ROLES as readonly string[]).includes(m.role));
  const ais = scoped.filter((m) => (AI_ROLES as readonly string[]).includes(m.role));

  // ADR-550 — the viewer's own standing, derived from the roster already
  // fetched (no second request, no role prop). The server marks the viewer's
  // own row by appending "(you)" to its label (routes/workspace.py:1357), so
  // the row is identifiable without a separate identity read.
  //
  // Why this is worth a header: the pane's prior line — "Everyone — and
  // everything — that can write to this workspace" — described the LIST but
  // never told the reader where THEY stood in it. A member and an owner saw
  // an identical sentence over a roster whose affordances differ entirely
  // (invite, narrow, revoke, cap are all owner-only). Naming the workspace and
  // the viewer's role is the smallest honest answer to "what am I looking at,
  // and what can I do here" — DP35's affordances-follow-the-grant, said in
  // words rather than left to be inferred from which buttons are missing.
  const viewerRow = members.find(
    (m) => (HUMAN_ROLES as readonly string[]).includes(m.role) && m.label?.includes('(you)'),
  );
  const viewerRole = viewerRow?.role as 'owner' | 'member' | 'viewer' | undefined;
  // The bound workspace's name. `getActiveWorkspaceId()` is deliberately NULL
  // for an owner on their own workspace (the switcher CLEARS the pin rather
  // than setting it — client.ts:142-148), so fall back to the membership whose
  // role matches the viewer's rather than assuming a pin exists.
  const activeWsId = typeof window === 'undefined' ? null : getActiveWorkspaceId();
  const workspaceLabel =
    memberships.find((w) => (activeWsId ? w.workspace_id === activeWsId : w.role === viewerRole))
      ?.label ?? null;
  const humanCount = members.filter((m) =>
    (HUMAN_ROLES as readonly string[]).includes(m.role),
  ).length;
  const aiCount = members.filter((m) => (AI_ROLES as readonly string[]).includes(m.role)).length;

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
        // ADR-496 D1 — `readOnly` drops the verbs entirely (the account-door
        // mirror READS; the workspace door GOVERNS — Singular Implementation).
        const governable = !readOnly && m.role !== 'owner';
        // ADR-431 §display — the one-line "what kind of principal is this" hint
        // that carries the conceptual framing. For an external LLM it names the
        // distinguishing fact: it reaches in autonomously over MCP and writes
        // as ITSELF — categorically unlike a member's in-chat model (which
        // writes as the member). Kept to a single short clause; no new data.
        const kindHint =
          m.role === 'foreign-llm'
            ? 'Connects over MCP · writes as itself'
            : m.role === 'own-agent'
            ? 'Workspace agent · writes as itself'
            : null;
        // ADR-431 D3 — WHO authorized this AI connection ("whose ChatGPT").
        // Resolves the operator's "whose?" question directly. "You" when the
        // viewer authorized it, else the member's email. Rendered as its own
        // prominent attribution line (not buried in the kind hint).
        // ADR-497 — `foreign-llm` is the only EXTERNAL principal class with a
        // creation path, so it alone gets the provider brand mark + the
        // connected-by attribution line. `own-agent` is internal (a hired
        // program, not someone's connection) and keeps the role glyph.
        const isExternalAI = m.role === 'foreign-llm';
        const connectedByName = m.connected_by_is_you ? 'You' : (m.connected_by_label ?? null);
        // ADR-563 — the token's verb tier, resolved to one operator-facing
        // label. Named for the CONSEQUENCE, not the scope string: the operator
        // is deciding about capability, not reading an OAuth field.
        const connectionTier = describeConnectionTier(
          m.connection_scopes ?? null,
          m.connection_legacy_full === true,
        );
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
                {/* ADR-445 §7 Phase 4 — the owner-set spend cap on the shared pool. */}
                {typeof m.spend_cap_usd === 'number' && m.spend_cap_usd > 0 && (
                  <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
                    <Wallet className="h-2.5 w-2.5" /> ${m.spend_cap_usd}/mo cap
                  </span>
                )}
              </div>
              {/* ADR-563 — the CONNECTION's verb tier. Deliberately its own
                  line, not another chip in the row above: that row is the PATH
                  axis (where this principal may reach), and this is the VERB
                  axis (what its token may do there). Merging them would imply
                  one narrows the other — a connector scoped to Documents can
                  still hold a token that deletes and shares within it.
                  Enforcement is `assert_scope`; this is the same table read for
                  display, so the pane cannot claim a tier the gate disagrees
                  with. */}
              {isExternalAI && connectionTier && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] text-muted-foreground/70">Can do:</span>
                  <span
                    className={cn(
                      'rounded px-1.5 py-0.5 text-[11px] font-medium',
                      connectionTier.tone,
                    )}
                  >
                    {connectionTier.label}
                  </span>
                  {m.connection_legacy_full && (
                    <span className="text-[10px] text-muted-foreground/60">
                      granted before scoped permissions existed
                    </span>
                  )}
                </div>
              )}
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
                        onClick={() => { setMenuFor(null); setCapTarget(m); }}
                        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted"
                      >
                        <Wallet className="h-3.5 w-3.5 text-muted-foreground" />
                        Set spend cap…
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
      {/* ADR-550 — the viewer's standing, not a description of the list.
          The section headings below already name the People/AI split, and each
          AI row states "Connects over MCP · writes as itself", so the old
          one-liner ("Everyone — and everything — that can write to this
          workspace") spent the pane's most prominent line restating the
          obvious while leaving the reader's OWN role to be inferred from which
          buttons were missing. */}
      {variant === 'full' && (
        <div className="rounded-lg border border-border bg-muted/30 px-4 py-3">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-sm font-medium text-foreground">
              {workspaceLabel ?? 'This workspace'}
            </span>
            {viewerRole && (
              <span
                className={cn(
                  'rounded-full px-2 py-0.5 text-xs font-medium',
                  viewerRole === 'owner'
                    ? 'bg-foreground text-background'
                    : 'bg-muted text-muted-foreground',
                )}
              >
                You&rsquo;re the {VIEWER_ROLE_LABEL[viewerRole]}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {viewerRole ? VIEWER_ROLE_HINT[viewerRole] : 'Who can write to this workspace.'}
          </p>
          <p className="mt-1.5 text-xs text-muted-foreground">
            {humanCount} {humanCount === 1 ? 'person' : 'people'}
            {aiCount > 0 && ` · ${aiCount} AI ${aiCount === 1 ? 'connection' : 'connections'}`}
          </p>
        </div>
      )}

      {/* ADR-404 step 5 — invite a human member (owner-only; hidden on 403). */}
      {variant === 'full' && canInvite && (
        <div className="rounded-lg border border-border p-3">
          {/* ADR-445 §6 — proactive seat awareness AT the invite affordance. The
              only headcount gate is the free→paid boundary: a Free workspace
              covers TWO humans (ADR-490 §1① — the owner + one teammate), so the
              3rd person needs the paid plan. A paid workspace grows freely (each
              new human a billed seat) — `available` is always true there, so this
              warning never shows. Surfaced before it's hit as a surprise 402.

              COPY FIX 2026-07-29: this said "The free plan is for one person" —
              the pre-ADR-490 boundary. ADR-490 moved free to two humans and the
              backend gate + `workspace_invites` copy followed; this string was
              the one that didn't, so a free workspace at its limit was told the
              wrong reason it was blocked. Derived from `included_seats` now, so a
              future boundary move cannot leave it stale again. */}
          {seatInfo && !seatInfo.available && (
            <p className="mb-2 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">
                The free plan covers{' '}
                {seatInfo.included === 1 ? 'one person' : `${seatInfo.included} people`}.
              </span>
              <span className="text-amber-600 dark:text-amber-400">
                {' '}Upgrade to the paid plan to invite your team.
              </span>
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
          {/* The "Members join this workspace with write access to Operation and
              Agents — every change they make is attributed to them. Narrow or
              revoke any time." helper is DELETED (2026-07-29, operator). It
              restated what the member rows already show: each row renders its own
              "Can write:" chips and a Narrow/Revoke menu, so the sentence was
              describing the controls sitting directly beneath it. */}
          {inviteError && <p className="mt-1.5 text-xs text-destructive">{inviteError}</p>}
          {lastInviteLink && (
            <p className="mt-1.5 break-all text-xs text-muted-foreground">
              Invite sent — share this link if the email doesn&rsquo;t arrive:{' '}
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
      {/* ADR-496 D1 — under `mine` the People section is omitted: "who else is
          in this workspace" is a commons question, answered on the workspace
          door. The account door answers only "what have I connected". */}
      {scope === 'workspace' && (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            People
          </h3>
          {humans.length === 0 ? renderEmptyState('No people yet') : renderMemberList(humans)}
        </section>
      )}

      {(ais.length > 0 || scope === 'mine') && (
        <section className="space-y-2">
          {/* The heading must say WHOSE roster this is, and it renders on BOTH
              doors from one component (ADR-496 D1: `mine` on the account door,
              `workspace` here). Audited against the grant table 2026-08-21:
              a connection is BOTH — workspace-scoped in its REACH
              (principal_grants is keyed workspace_id; prod carries the same
              person's claude.ai as two separate grants in two workspaces, so a
              connection here grants nothing there) and member-owned in its
              AUTHORIZATION (ADR-431, "the connecting member owns the MCP
              grant" — `connected_by`, torn down on that member's eviction).
              Naming only one half is what made the section ambiguous: on the
              workspace door "AI connections" read as if it might be listing a
              person's connections generally. */}
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {scope === 'mine'
              ? 'AI connections'
              : 'AI connections to this workspace'}
          </h3>
          {scope === 'workspace' && ais.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Each reaches only this workspace, under the grant of the member
              who connected it — and goes away when they do.
            </p>
          )}
          {ais.length > 0
            ? renderMemberList(ais)
            : renderEmptyState(
                'No AI connections yet',
                'Connect this workspace from ChatGPT or Claude to give it durable, attributed memory.',
              )}
        </section>
      )}

      {footer}

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
            {governError && (
              <p role="alert" className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-[13px] text-destructive">
                {governError}
              </p>
            )}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => { setGovernError(null); setRevokeTarget(null); }}
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
          error={governError}
          onCancel={() => { setGovernError(null); setNarrowTarget(null); }}
          onConfirm={(write, read) => onNarrow(narrowTarget, write, read)}
        />
      )}

      {/* ADR-445 §7 Phase 4 — SPEND CAP: bound the member's draw of the shared pool. */}
      {capTarget && (
        <CapDialog
          member={capTarget}
          busy={busy}
          error={governError}
          onCancel={() => { setGovernError(null); setCapTarget(null); }}
          onConfirm={(cap) => onCap(capTarget, cap)}
        />
      )}
    </div>
  );
}

/**
 * CapDialog — set (or clear) a member's monthly spend cap on the shared pool
 * (ADR-445 §7 Phase 4). The cap bounds ONE principal's draw; usage is still the
 * shared pool (a cap is safety, not a per-member bucket — ADR-445 §4). Clearing
 * leaves the member uncapped (draws the whole pool, backstopped by the hard-stop).
 */
function CapDialog({
  member,
  busy,
  error,
  onCancel,
  onConfirm,
}: {
  member: Member;
  busy: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: (capUsd: number | null) => void;
}) {
  const [value, setValue] = useState<string>(
    typeof member.spend_cap_usd === 'number' && member.spend_cap_usd > 0
      ? String(member.spend_cap_usd)
      : '',
  );
  const parsed = value.trim() === '' ? null : Number(value);
  const invalid = value.trim() !== '' && (!Number.isFinite(parsed) || (parsed as number) <= 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => !busy && onCancel()}>
      <div className="w-full max-w-md rounded-lg border border-border bg-background p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-foreground">
          Set {member.label ?? member.principal_id}&rsquo;s spend cap
        </h3>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Bound how much this member may draw from the workspace&rsquo;s shared usage pool
          each cycle. They stay a member and keep their access — only their spend is
          capped. Leave blank to remove the cap (they draw the whole pool, up to the
          workspace balance).
        </p>
        <div className="mt-4 flex items-center gap-2">
          <span className="text-sm text-muted-foreground">$</span>
          <input
            type="number"
            min="0"
            step="1"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="no cap"
            className="min-w-0 flex-1 rounded-md border border-input bg-background px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            aria-label="Monthly spend cap in dollars"
          />
          <span className="text-xs text-muted-foreground">/ month</span>
        </div>
        {invalid && <p className="mt-1.5 text-xs text-destructive">Enter a positive dollar amount, or leave blank to clear.</p>}
        {error && (
          <p role="alert" className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-[13px] text-destructive">
            {error}
          </p>
        )}
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
            disabled={busy || invalid}
            onClick={() => onConfirm(parsed)}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {parsed === null ? 'Remove cap' : 'Set cap'}
          </button>
        </div>
      </div>
    </div>
  );
}

// The three access levels an operator assigns per path (powerbox two-axis).
// 'none' = the path is not in either scope; 'read' = read-only (read scope only);
// 'write' = read + write (in both scopes — read ⊇ write, the norm).
/** ADR-532 (recut) — the three states a grant can be in, and the only three
 *  the kernel can express: `narrow` never widens, so an operator picks the
 *  class default, a subset of it, or nothing. */
type AccessMode = 'full' | 'restricted' | 'none';

/** True iff `path` is inside what this principal's grant can reach TODAY —
 *  the same subset rule `narrow_grant::_within` enforces server-side.
 *
 *  Offering a quick-pick the server must refuse is the "a scope that exists is
 *  not a scope you can enter" defect: the first cut shipped `+ Agents`, and
 *  `agents/` is outside the `operation/` class ceiling, so it 400'd every time.
 *  The gate still enforces; this only keeps unusable options off the screen. */
function withinCeiling(path: string, member: Member): boolean {
  const ceiling =
    member.write_state === 'scoped' ? member.write_regions.map(normalizePrefix) : ['operation/'];
  return ceiling.some((c) => path === c || path.startsWith(c));
}

/** Sentence-case opener for the dialog's lede. */
function roleNounCap(role: string): string {
  const n = roleNoun(role);
  return n.charAt(0).toUpperCase() + n.slice(1);
}

/** ADR-532 D1 — how to name a principal's class in the "not narrowed" line.
 *  Species-blind (ADR-405): this describes the CLASS DEFAULT the grant falls
 *  through to, never a permission derived from the role. */
function roleNoun(role: string): string {
  switch (role) {
    case 'owner':
      return 'an owner';
    case 'viewer':
      return 'a viewer';
    case 'foreign-llm':
      return 'a connected AI';
    case 'own-agent':
      return 'a hired agent';
    default:
      return 'a member';
  }
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
  error,
  onCancel,
  onConfirm,
}: {
  member: Member;
  busy: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: (writeScopes: string[], readScopes: string[]) => void;
}) {
  // ADR-532 (recut 2026-08-07) — the dialog asks ONE question, because the
  // kernel only answers one.
  //
  // `narrow_grant` is NARROW-ONLY: it raises ScopeEscalation on any widening,
  // and the class ceiling for both `member` and `foreign-llm` is `operation/`.
  // So the entire expressible space is: the class default, a subset of it, or
  // nothing. The previous cut shipped a general-purpose grant EDITOR over that
  // — free-text paths, per-row read/write toggles, and an `+ Agents` quick-pick
  // that could never succeed (`agents/` is outside the ceiling, so clicking it
  // and applying returned a 400). A control that exists but cannot be entered
  // is the defect this ADR was written to remove, reintroduced one layer up.
  //
  // Three states, one radio group. Species-blind (ADR-405): a human, a
  // connected LLM, and a hired agent get the SAME control — the row's kind
  // changes the label copy, never the model.
  const initialMode: AccessMode =
    member.write_state === 'all' && member.read_state === 'all'
      ? 'full'
      : member.write_state === 'none' && member.read_state === 'none'
        ? 'none'
        : 'restricted';

  const [mode, setMode] = useState<AccessMode>(initialMode);
  const [paths, setPaths] = useState<string[]>(() =>
    Array.from(
      new Set(
        [...member.write_regions, ...(member.read_scopes ?? [])]
          .map(normalizePrefix)
          .filter(Boolean),
      ),
    ),
  );
  const [newPath, setNewPath] = useState('');

  // Nothing to apply until the operator actually changes something. Inspecting
  // a principal must never narrow it (the D1 defect, kept fixed).
  const dirty = mode !== initialMode || (mode === 'restricted' && paths.join(' ') !== Array.from(
    new Set([...member.write_regions, ...(member.read_scopes ?? [])].map(normalizePrefix).filter(Boolean)),
  ).join(' '));

  const addPath = () => {
    const p = normalizePrefix(newPath);
    if (!p || paths.includes(p)) return;
    setPaths((ps) => [...ps, p]);
    setNewPath('');
  };

  // The wire payload for each mode. Both axes move together — `narrow_grant`'s
  // own default is `read ⊇ write` with read mirroring write, so a per-path read
  // axis would be UI carrying a distinction nothing sets. (ADR-434 D1's
  // read-only auditor stays representable in the KERNEL and reachable via the
  // API; it is simply not a cockpit control until something asks for it.)
  //
  //   full       → null  = class default, the un-narrowed grant
  //   restricted → paths = allow-list, at any depth under the class ceiling
  //   none       → []    = explicit deny-all, still connected
  const scopesForMode = (): string[] | null =>
    mode === 'full' ? null : mode === 'none' ? [] : paths;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => !busy && onCancel()}>
      <div className="w-full max-w-lg rounded-lg border border-border bg-background p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-foreground">
          Set {member.label ?? member.principal_id}&rsquo;s access
        </h3>
        <p className="mt-1.5 text-sm text-muted-foreground">
          {roleNounCap(member.role)} access to this workspace. Anything not
          granted is hidden and denied — {member.label ?? 'they'} stays connected
          either way.
        </p>

        {/* ADR-532 (recut) — ONE radio group. The kernel's `narrow` verb only
            tightens, and the class ceiling is `operation/`, so this is the whole
            expressible space. Species-blind: identical for a person, a connected
            LLM, and a hired agent. */}
        <div className="mt-4 space-y-1.5">
          {(
            [
              ['full', 'Full access', `Everything ${roleNoun(member.role)} can reach. The default.`],
              ['restricted', 'Only these paths', 'A folder or a single file. Everything else is hidden.'],
              ['none', 'No access', 'Reads and writes nothing. Still connected — use Revoke to disconnect.'],
            ] as [AccessMode, string, string][]
          ).map(([value, label, hint]) => (
            <label
              key={value}
              className={cn(
                'flex cursor-pointer items-start gap-2.5 rounded-md border px-3 py-2.5',
                mode === value ? 'border-primary bg-primary/5' : 'border-border/60 hover:bg-muted/40',
              )}
            >
              <input
                type="radio"
                name="access-mode"
                checked={mode === value}
                onChange={() => setMode(value)}
                className="mt-0.5"
              />
              <span className="min-w-0">
                <span className="block text-[13px] font-medium text-foreground">{label}</span>
                <span className="block text-[12px] text-muted-foreground">{hint}</span>
              </span>
            </label>
          ))}
        </div>

        {/* The path list — only when it means something. */}
        {mode === 'restricted' && (
          <div className="mt-3 space-y-1.5 rounded-md border border-border/60 p-3">
            {paths.length === 0 && (
              <p className="text-[12px] text-muted-foreground">
                Add at least one path — an empty list means no access.
              </p>
            )}
            {paths.map((p) => (
              <div key={p} className="flex items-center gap-2 rounded border border-border/60 px-2.5 py-1.5">
                <code className="min-w-0 flex-1 truncate text-[12px] text-foreground/80" title={p}>{p}</code>
                <button
                  type="button"
                  onClick={() => setPaths((ps) => ps.filter((x) => x !== p))}
                  className="shrink-0 rounded px-1.5 py-0.5 text-[12px] text-muted-foreground hover:bg-muted"
                  aria-label={`Remove ${p}`}
                >
                  ✕
                </button>
              </div>
            ))}
            {/* Quick-pick: only regions actually INSIDE the class ceiling. An
                option that always 400s is worse than no option (the `+ Agents`
                defect of the first cut). */}
            <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
              {NARROWABLE_REGIONS.filter(
                (rg) => !paths.includes(normalizePrefix(rg)) && withinCeiling(normalizePrefix(rg), member),
              ).map((region) => (
                <button
                  key={region}
                  type="button"
                  onClick={() => setPaths((ps) => [...ps, normalizePrefix(region)])}
                  className="inline-flex items-center gap-1 rounded-md border border-dashed border-border px-2 py-1 text-[12px] text-muted-foreground hover:bg-muted/50"
                >
                  <Plus className="h-3 w-3" /> {regionLabel(region)}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 pt-1">
              <input
                value={newPath}
                onChange={(e) => setNewPath(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addPath())}
                placeholder="e.g. operation/marketing/ or operation/reports/q3.md"
                className="min-w-0 flex-1 rounded-md border border-input bg-background px-2.5 py-1.5 text-[12px] focus:outline-none focus:ring-1 focus:ring-ring"
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
          </div>
        )}

        {/* No summary line. The radio label IS the statement of what will
            happen — a second restatement is where "Not narrowed" and
            "Read: nothing · Write: nothing" ended up contradicting each other
            on the same screen. */}

        {error && (
          <p role="alert" className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-[13px] text-destructive">
            {error}
          </p>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onCancel}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            Cancel
          </button>
          {/* Inert until something actually changed — inspecting a principal
              must never narrow it. `restricted` with an empty list is also
              inert: it would silently mean deny-all, which is what the third
              radio says out loud. */}
          <button
            type="button"
            disabled={busy || !dirty || (mode === 'restricted' && paths.length === 0)}
            onClick={() => {
              const scopes = scopesForMode();
              onConfirm(scopes as string[], scopes as string[]);
            }}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50',
              mode === 'none'
                ? 'bg-amber-600 text-white hover:bg-amber-600/90'
                : 'bg-primary text-primary-foreground hover:bg-primary/90',
            )}
          >
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {mode === 'none' ? 'Remove all access' : 'Apply'}
          </button>
        </div>
      </div>
    </div>
  );
}
