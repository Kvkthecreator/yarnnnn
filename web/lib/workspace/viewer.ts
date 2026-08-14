'use client';

/**
 * Viewer resolution — the ADR-412 D6 layer over the attribution module.
 *
 * The sync labeler (attribution.ts) maps `authored_by` strings to generic
 * labels; in a multi-principal commons the VIEWER matters: the same act
 * renders "You" to its actor and "seulkim88" to a peer (ADR-405 D4 — you
 * don't need to be told what you just did; ADR-410 D1 — the bell shows
 * peer/agent acts only). This module supplies:
 *
 *   - useWorkspaceMembers(): the workspace's principal roster (full rows —
 *     principal_id, role, label, write_regions), fetched once per workspace
 *     bind and cached module-level (membership is a slow fact, not presence).
 *   - useWorkspaceRoster(): the same roster projected to principal_id → label
 *     (what the attribution resolution needs).
 *   - useWorkspaceMemberships(): the workspaces the CALLER can act in
 *     (ADR-407 Phase 5) — powers the ADR-412 D6 which-workspace ambient
 *     indicator + the UserMenu switcher off ONE cached fetch.
 *   - useViewerGrant(): the viewer's own write-region coverage — the
 *     grant-derived affordance source (ADR-412 D6: affordances render per
 *     grant coverage, NEVER a role enum). FE gating is legibility only;
 *     the server gate is enforcement.
 *   - resolveActorForViewer(): actor string + acting-principal uuid →
 *     { label, isSelf }, first-person resolved.
 *
 * One module, one added layer above attribution.ts (ADR-388 D3 discipline —
 * no parallel labeler; non-human classes pass through the existing one).
 */

import { useEffect, useState } from 'react';
import { api, getActiveWorkspaceId } from '@/lib/api/client';
import {
  formatAuthorLabelOrSystem,
  memberEmbodiment,
} from '@/lib/workspace/attribution';

/** One principal of the acting workspace (GET /api/workspace/members row). */
export interface WorkspaceMemberRow {
  principal_id: string;
  role: string; // owner | member | viewer | own-agent | foreign-llm | platform | a2a
  label: string | null;
  write_regions: string[];
  scopes_explicit: boolean;
  status: string;
}

/** One workspace the caller can act in (GET /api/workspace/memberships row). */
export interface WorkspaceMembershipRow {
  workspace_id: string;
  // ADR-517 D6 — viewer included: a viewer can enter the workspace they view.
  role: 'owner' | 'member' | 'viewer';
  label: string;
  is_active: boolean;
  /** Workspace identity phase 1 — owner-chosen glyph (emoji); null/absent →
   *  the default org glyph. */
  icon?: string | null;
}

export interface WorkspaceRoster {
  /** principal_id → humanized label (email local part / LLM room / slug). */
  labels: Map<string, string>;
  loaded: boolean;
}

// Module-level caches: membership is a slow fact; one fetch per page life is
// enough — PROVIDED the acting workspace can't change under the cache.
//
// ADR-500: that proviso used to hold (the workspace switcher hard-reloads on
// bind change, ADR-407 D9), but ADR-499's stale-pin self-heal rebinds MID-
// SESSION with no reload. A roster fetched under the old binding then outlived
// it, so the chat picker offered a person from the previous workspace and the
// server correctly 422'd ("that person isn't in this workspace") on a choice
// the FE should never have presented.
//
// The cache is therefore keyed to the BINDING it was fetched under. A binding
// change invalidates by construction — no invalidation call to remember at the
// (now several) sites that can rebind.
let membersPromise: Promise<WorkspaceMemberRow[]> | null = null;
let membershipsPromise: Promise<WorkspaceMembershipRow[]> | null = null;
let cacheBinding: string | null | undefined;

/** Drop the caches when the acting workspace differs from the one they were
 *  fetched under. Cheap (a string compare) and called on every hook read. */
function syncCacheBinding(): void {
  const current = getActiveWorkspaceId();
  if (cacheBinding === undefined) {
    cacheBinding = current;
    return;
  }
  if (cacheBinding !== current) {
    membersPromise = null;
    membershipsPromise = null;
    cacheBinding = current;
  }
}

/** Distinguishes "no access to this workspace" from "roster unavailable".
 *
 * A 403 is a FACT about the viewer (revoked, or never granted); any other
 * failure is transport noise. Collapsing both to `[]` made a revoked member's
 * settings surface render its full chrome as though nothing had changed —
 * every pane 403'd underneath, so it was chrome without data (2026-07-31
 * click-pass F3). Surfaces can now say so. */
let membersForbidden = false;

async function fetchMembers(): Promise<WorkspaceMemberRow[]> {
  try {
    const res = await api.workspace.getMembers();
    membersForbidden = false;
    return res.members || [];
  } catch (e) {
    // Roster unavailable — resolution degrades to the generic labeler and
    // grant-derived affordances fail OPEN (the server gate still enforces).
    const status =
      e && typeof e === 'object' && 'status' in e
        ? (e as { status?: number }).status
        : undefined;
    membersForbidden = status === 403;
    return [];
  }
}

/** True when the LAST memberships fetch failed (as opposed to genuinely
 *  returning no rows). Read by the switcher so a failed read degrades to
 *  "we couldn't load this" instead of "you belong to nothing". */
let membershipsFailed = false;

async function fetchMemberships(): Promise<WorkspaceMembershipRow[]> {
  try {
    const res = await api.workspace.memberships();
    membershipsFailed = false;
    return res.memberships || [];
  } catch {
    // A FAILURE IS NOT AN EMPTY LIST, and — load-bearing — it must not be
    // CACHED as one.
    //
    // Observed on production 2026-08-07: one transient 403 on
    // `/api/workspace/memberships` (a stale `X-Workspace-Id` pin, which
    // ADR-499's self-heal then cleared and retried successfully) emptied the
    // switcher for the REST OF THE PAGE'S LIFE. The retry succeeded; nothing
    // re-read it. `membershipsPromise` had already resolved to `[]`, and
    // `syncCacheBinding` only invalidates on a BINDING change — the pin went
    // from stale-value to null, which is a change the member never sees
    // because the menu was already gone. The operator's whole WORKSPACE
    // section vanished, including "My workspace", which every owner always
    // has.
    //
    // The cache is dropped by the READER (see `useWorkspaceMemberships`), not
    // here: this function runs INSIDE `membershipsPromise = fetchMemberships()`,
    // so clearing the variable here is immediately overwritten by that pending
    // assignment. Caught by executing the two orderings side by side rather
    // than reasoning about them.
    membershipsFailed = true;
    return [];
  }
}

export function useWorkspaceMembers(): {
  members: WorkspaceMemberRow[];
  loaded: boolean;
  /** True when the roster read was REFUSED (403) — the viewer has no grant on
   *  the bound workspace. Distinct from `members: []`, which also covers a
   *  transport blip and an empty roster. */
  forbidden: boolean;
} {
  const [state, setState] = useState<{
    members: WorkspaceMemberRow[];
    loaded: boolean;
    forbidden: boolean;
  }>({ members: [], loaded: false, forbidden: false });
  useEffect(() => {
    let cancelled = false;
    syncCacheBinding();
    if (!membersPromise) membersPromise = fetchMembers();
    membersPromise.then((members) => {
      if (!cancelled) setState({ members, loaded: true, forbidden: membersForbidden });
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return state;
}

export function useWorkspaceRoster(): WorkspaceRoster {
  const { members, loaded } = useWorkspaceMembers();
  const labels = new Map<string, string>();
  for (const m of members) {
    if (m.principal_id) labels.set(m.principal_id, m.label || m.principal_id);
  }
  return { labels, loaded };
}

export function useWorkspaceMemberships(): {
  memberships: WorkspaceMembershipRow[];
  loaded: boolean;
  /** True when the read FAILED, as opposed to returning no rows. `[]` alone
   *  cannot be trusted to mean "you belong to nothing" — every owner belongs
   *  to at least their own workspace, so an empty list is nearly always a
   *  failure in disguise. */
  failed: boolean;
} {
  const [state, setState] = useState<{
    memberships: WorkspaceMembershipRow[];
    loaded: boolean;
    failed: boolean;
  }>({ memberships: [], loaded: false, failed: false });
  useEffect(() => {
    let cancelled = false;
    syncCacheBinding();
    if (!membershipsPromise) membershipsPromise = fetchMemberships();
    membershipsPromise.then((memberships) => {
      // Drop the cache HERE, after the assignment above has settled, so a
      // failed read is genuinely retried by the next mount instead of being
      // served from cache for the rest of the page's life.
      if (membershipsFailed) membershipsPromise = null;
      if (!cancelled) setState({ memberships, loaded: true, failed: membershipsFailed });
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return state;
}

// ---------------------------------------------------------------------------
// Grant-derived affordances (ADR-412 D6/D3)
// ---------------------------------------------------------------------------

export interface ViewerGrant {
  loaded: boolean;
  /** The viewer's resolved write-region set; null while unresolved (loading,
   *  roster unavailable, or no row for the viewer) → affordances fail OPEN. */
  writeRegions: string[] | null;
  /** True iff the viewer's grant covers writes under `regionRoot` (e.g.
   *  'constitution/'). Unresolved → true (legibility gate only — the server
   *  gate is enforcement, so failing open never grants anything). */
  covers: (regionRoot: string) => boolean;
}

/**
 * The viewer's own grant coverage — the ADR-412 D3/D6 affordance source.
 * Derived from the SAME roster fetch as attribution (one substrate, one
 * fetch). The check is region coverage from `write_regions`, NEVER the role
 * enum — the UI twin of ADR-405's no-species-law.
 */
export function useViewerGrant(viewerId: string | null | undefined): ViewerGrant {
  const { members, loaded } = useWorkspaceMembers();
  const row = viewerId
    ? members.find((m) => m.principal_id === viewerId)
    : undefined;
  const writeRegions = loaded && row ? row.write_regions : null;
  const covers = (regionRoot: string): boolean => {
    if (writeRegions == null) return true; // unresolved → fail open
    return writeRegions.some((r) => regionRoot.startsWith(r) || r.startsWith(regionRoot));
  };
  return { loaded, writeRegions, covers };
}

// ---------------------------------------------------------------------------
// Actor resolution
// ---------------------------------------------------------------------------

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-/i;

export interface ResolvedActor {
  label: string;
  isSelf: boolean;
}

/**
 * First-person resolution of a timeline/ledger actor.
 *
 * @param actor    the ledger's actor string (authored_by taxonomy, a raw
 *                 principal uuid for invocations, or a proposal source)
 * @param actorId  the acting principal's uuid where the ledger records one
 *                 (revisions: author_identity_uuid; invocations:
 *                 principal_id)
 * @param viewerId the viewing principal's uuid
 *
 * Legacy note: pre-ADR-410 `operator` revisions carry no actorId — those
 * resolve as SELF (quiet default: showing the viewer their own old writes
 * as peer activity is noise; new writes carry identity, and the read
 * cursor ages legacy rows out of the unseen count quickly).
 */
export function resolveActorForViewer(
  actor: string | null | undefined,
  actorId: string | null | undefined,
  viewerId: string | null | undefined,
  roster: WorkspaceRoster,
): ResolvedActor {
  const peerLabel = (id: string) => roster.labels.get(id) ?? 'A member';

  // Lane embodiment — "You via GPT-4o mini" / "‹member› via ‹model›".
  const emb = memberEmbodiment(actor);
  if (emb) {
    const isSelf = !!viewerId && emb.memberId === viewerId;
    const base = formatAuthorLabelOrSystem(actor); // "Member (via ‹Model›)"
    const via = base.includes('(via') ? base.slice(base.indexOf('(via')) : '';
    const who = isSelf ? 'You' : peerLabel(emb.memberId);
    return { label: via ? `${who} ${via}` : who, isSelf };
  }

  // Direct human act (operator-class revision).
  if (actor === 'operator') {
    if (actorId) {
      const isSelf = !!viewerId && actorId === viewerId;
      return { label: isSelf ? 'You' : peerLabel(actorId), isSelf };
    }
    return { label: 'You', isSelf: true }; // legacy identity-less row
  }

  // Raw principal uuid (invocation principal_id for a human principal).
  if (actor && UUID_RE.test(actor)) {
    const isSelf = !!viewerId && actor === viewerId;
    return { label: isSelf ? 'You' : peerLabel(actor), isSelf };
  }

  // Everything else (freddie:, agent:, system:, yarnnn:mcp:, provider
  // host ids) — the existing labeler; never self.
  return { label: formatAuthorLabelOrSystem(actor), isSelf: false };
}
