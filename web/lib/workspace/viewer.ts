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
 *   - useWorkspaceRoster(): the workspace's principal roster
 *     (principal_id → label), fetched once per workspace bind and cached
 *     module-level (membership is a slow fact, not presence).
 *   - resolveActorForViewer(): actor string + acting-principal uuid →
 *     { label, isSelf }, first-person resolved.
 *
 * One module, one added layer above attribution.ts (ADR-388 D3 discipline —
 * no parallel labeler; non-human classes pass through the existing one).
 */

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import {
  formatAuthorLabelOrSystem,
  memberEmbodiment,
} from '@/lib/workspace/attribution';

export interface WorkspaceRoster {
  /** principal_id → humanized label (email local part / LLM room / slug). */
  labels: Map<string, string>;
  loaded: boolean;
}

// Module-level cache: the roster is a slow fact; one fetch per page life is
// enough (the workspace switcher hard-reloads on bind change, ADR-407 D9).
let rosterPromise: Promise<Map<string, string>> | null = null;

async function fetchRoster(): Promise<Map<string, string>> {
  const labels = new Map<string, string>();
  try {
    const res = await api.workspace.getMembers();
    for (const m of res.members || []) {
      if (m.principal_id) labels.set(m.principal_id, m.label || m.principal_id);
    }
  } catch {
    // Roster unavailable — resolution degrades to the generic labeler.
  }
  return labels;
}

export function useWorkspaceRoster(): WorkspaceRoster {
  const [roster, setRoster] = useState<WorkspaceRoster>({
    labels: new Map(),
    loaded: false,
  });
  useEffect(() => {
    let cancelled = false;
    if (!rosterPromise) rosterPromise = fetchRoster();
    rosterPromise.then((labels) => {
      if (!cancelled) setRoster({ labels, loaded: true });
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return roster;
}

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
