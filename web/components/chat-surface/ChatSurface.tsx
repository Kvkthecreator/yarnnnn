'use client';

/**
 * ChatSurface — the chat workbench (ADR-412 D3/D4).
 *
 * Your conversations with colleagues (ADR-411 lanes) as a windowed surface —
 * a working area summoned like any window, distinct from the steward rail
 * (the chat drawer) and the Agents roster (who they are).
 *
 * ⚠️ VOCABULARY (ADR-460 D1, corrected 2026-07-22 — §6.10d). This header used
 * to place the surface on a three-rung ladder ("A2's chrome home", vs the
 * rail's A1 and the roster's A3). **ADR-460 D1 RETIRED that ladder** — it was a bundle of
 * four independent facts (attribution · configuration · standing intent ·
 * governance files) wearing an ordinal, and the runtime never had it
 * (`_caller_class` branches on the author prefix, not a rung). Say instead:
 * an Agent that attributes as the member (these chats) vs one that attributes
 * as itself. Do not reintroduce the ladder in comments — it is the vocabulary
 * the next session reads to decide what an Agent is.
 *
 * D4 — lanes organize by WORK, never by model: the list is flat recents
 * (updated_at desc — the API touches updated_at on every turn), each row
 * named by its work with the pinned model as a CHIP; a model FILTER facet
 * gives the by-engine view on demand. Model-first folders are rejected
 * (ADR-385 precedent: group by relationship, never transport).
 *
 * The guardrail (ADR-412 D3): this is a workbench over the shared
 * workspace, not the product's center — the ADR-411 contract is restated
 * in the empty states (lanes are isolated conversations; the workspace is
 * the shared memory; the work lands in files, attributed).
 *
 * Member-experience scope: `GET /api/lanes` returns only the viewer's
 * lanes in the acting workspace (ADR-407 D6). Active lane deep-links via
 * the window-namespaced `chat.lane` param (ADR-358 D6).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Archive, Loader2, MessageCircle, Pencil, Pin, Plus, Search, X } from 'lucide-react';
import { LanePanel } from './LanePanel';
import { ConversationHeader, type HeaderFace } from './ConversationHeader';
import { ConversationDetail } from './ConversationDetail';
import { AgentFace } from '@/components/agents/AgentFace';
import { NewChatModal } from './NewChatModal';
import { useWorkspaceMembers } from '@/lib/workspace/viewer';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { api, type Participant } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';
import { engineBrandIcon } from '@/lib/ai-providers/brand-icons';
import { cn } from '@/lib/utils';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useNarrowContainer } from '@/lib/shell/useNarrowContainer';
import { useSelfLocatedSurface, useWindowCrumb } from '@/contexts/BreadcrumbContext';

/** The width below which the chat surface stops being two columns.
 *
 *  The rail is `w-72` (288px) and a transcript needs roughly as much again to
 *  be readable, so under ~600px of surface the two-column layout is worse than
 *  one screen at a time. Measured against the SURFACE's own box (see
 *  `useNarrowContainer`), never the viewport — the viewport says "desktop" for
 *  a 768px tablet and for a 320px window alike, and both leave the transcript
 *  a sliver. */
const CHAT_TWO_COLUMN_MIN_PX = 600;

interface LaneInfo {
  id: string;
  name: string;
  model: string;
  /** ADR-460 D4 — WHO this lane talks to. Absent on pre-registry lanes and on
   *  Studio/derive lanes: the UI falls back to the model label, which is
   *  honest (that IS what those lanes are) rather than guessed. */
  agent?: string | null;
  /** Phase-A hygiene: pinned lanes sort first. */
  pinned?: boolean;
  updated_at?: string;
  created_at?: string;
  /** ADR-450 D3 — the derive binding (null/absent for plain chat lanes). */
  derive_recipe?: string | null;
  derive_source?: string | null;
  /** ADR-495 D1 — the cast, seeded from the list so the bar paints at once. */
  participants?: Participant[];
}

interface LaneData {
  enabled: boolean;
  /** ADR-460 D4 — the chooser: named colleagues, not a spec sheet. The member
   *  picks WHO; the engine rides behind the name. */
  agents?: Array<{
    slug: string; name: string; blurb: string; icon: string;
    color?: string; avatar?: string; based_on?: string; tone?: string;
    /** The image reference the FE trades for a signed URL (ADR-395). */
    avatar_url?: string;
    /** The capability's name (Critic) + the engine's label (GPT-5) — the
     *  technical fact stays VISIBLE, it just isn't the headline. */
    role?: string; engine?: string;
    /** kernel = a built-in capability; false = one the member hired + named. */
    kernel?: boolean;
  }>;
  /** Still served: every model stays routable (Studio/derive bind one
   *  directly, and the lane filter facet reads it). The registry changes what
   *  the CHOOSER asks, not what the system can run. */
  models: Array<{ id: string; label: string; vision?: boolean;
          /** ADR-559 D3 — false when the engine cannot run right now.
           *  Served (not filtered) so the door can grey it WITH a reason. */
          available?: boolean; unavailable_reason?: string | null }>;
  /** ADR-450 D5 — kernel recipes (the Learn-from chooser payload). */
  recipes?: Array<{ slug: string; label: string; description: string }>;
  lanes: LaneInfo[];
}

export function ChatSurface() {
  const [data, setData] = useState<LaneData | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  // D4 — the FILTER facet (null = all lanes, the default view). ADR-460: it
  // filters by WHO you talked to, not by which engine ran — the last
  // spec-sheet surface in chat, re-axed. A lane with no agent (pre-registry,
  // Studio/derive) files under its engine label, which is honest: that IS
  // what those lanes are.
  const [whoFilter, setWhoFilter] = useState<string | null>(null);
  // Phase-A hygiene: search (name locally + transcript content server-side,
  // debounced) and inline rename state.
  const [query, setQuery] = useState('');
  const [contentHits, setContentHits] = useState<Set<string> | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameText, setRenameText] = useState('');
  const { get: getParam, set: setParam } = useSurfaceParam('chat');
  // ADR-495 — ONE object. There is no `?room` param and no second list: a
  // conversation is participants + turns, and `?lane` names it whatever its
  // cast size. ("lane" survives as the param slug only — relabel-keep-slug,
  // the same grandfathering as `session_type='lane'`.)
  const activeLaneId = getParam('lane');
  // The participants drill-in, deep-linkable like every other intra-surface
  // navigation (`chat.detail=participants`, ADR-358 D6) — the
  // ManageConnectionSubsurface convention, not a modal.
  // Two doors into ONE pane: `participants` inspects the cast, `add` opens the
  // same pane with the invite already open. Separate params because they are
  // separate ACTS (the header offers both), one component because they are the
  // same place — a second component would be two rosters to keep in step.
  const detailParam = getParam('detail');
  const showDetail = detailParam === 'participants' || detailParam === 'add';
  // ADR-514 D2.3 — files arriving by `reference` delivery ("Open With → Chat").
  // Space-separated (paths cannot contain spaces here) so one param carries a
  // multi-selection; memoized so the identity is stable and the composer's
  // consume-once guard is not re-armed by every render.
  const citeParam = getParam('cite');
  const citePaths = useMemo(
    () => (citeParam ? citeParam.split(' ').filter(Boolean) : undefined),
    [citeParam],
  );
  const { userId } = useSurfacePreferences();
  const { members: wsMembers } = useWorkspaceMembers();
  // The workspace's other humans — invitable into any conversation (ADR-495
  // D3: one species-blind invite; a person is a participant like any other).
  const people = useMemo(
    () =>
      wsMembers
        .filter((m) => (m.role === 'owner' || m.role === 'member') && m.principal_id !== userId)
        .map((m) => ({ principal_id: m.principal_id, label: m.label || `member-${m.principal_id.slice(0, 8)}` })),
    [wsMembers, userId],
  );
  // One screen at a time when the space is tight (the Files/SettingsPaneShell
  // principle): the lane list IS the screen until you pick a lane, then the
  // conversation IS the screen.
  //
  // Measured on THIS surface's own box, not the viewport. Keying it to
  // `useViewport().isMobile` asked the window a question only the container can
  // answer, and got it wrong in both directions: a 768px tablet reads
  // "desktop" (the threshold is 640) and gets a 288px `shrink-0` rail that can
  // leave ~80px of transcript once the chat drawer takes its 400px; and a 320px
  // WINDOW on a large monitor reads "desktop" too, leaving ~32px. Observing the
  // element covers both, and is what the Studio canvas already does.
  //
  // The threshold is the width below which two columns stop being two columns:
  // the 288px rail plus a transcript wide enough to read.
  const surfaceRef = useRef<HTMLDivElement>(null);
  const isNarrow = useNarrowContainer(surfaceRef, CHAT_TWO_COLUMN_MIN_PX);

  // Debounced transcript search — content matches union with name matches.
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setContentHits(null);
      return;
    }
    const t = setTimeout(() => {
      api.lanes
        .search(q)
        .then((res) => setContentHits(new Set(res.matches.map((m) => m.lane_id))))
        .catch(() => setContentHits(null));
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    api.lanes
      .list()
      .then((res) => {
        if (cancelled) return;
        setData(res as LaneData);
      })
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const modelLabel = useCallback(
    (modelId: string) => data?.models.find((m) => m.id === modelId)?.label ?? modelId,
    [data],
  );

  // ADR-558 D3 — `lane.agent` is a BOUND lane's resident (Studio · Docs ·
  // IMAGES pin a colleague, ADR-467 D1). A CHAT lane never carries one: the
  // server refuses it at creation, so this resolves to null for every
  // conversation on this surface and the engine label answers instead.
  //
  // Kept, not deleted, because bound lanes DO reach a few of these helpers
  // (they have no participant rows to name themselves from). Deleting it would
  // make a Studio lane render as an engine where it should render as Designer.
  const laneAgent = useCallback(
    (lane: { agent?: string | null }) =>
      (lane.agent && data?.agents?.find((a) => a.slug === lane.agent)) || null,
    [data],
  );
  // Direct conversations (2+ humans, no agent in the cast): the conversation
  // is WITH the other humans, so it is labeled by THEM — never by the dormant
  // engine (operator-observed 2026-07-29: a chat with a person read "Claude
  // Sonnet" in the list and header). The cast rides on every list row
  // (ADR-495 D1), so this derives locally.
  const laneOtherHumans = useCallback(
    (lane: { agent?: string | null; participants?: Participant[] }) => {
      const cast = lane.participants ?? [];
      return cast
        .filter((p) => p.member_kind === 'human' && p.principal_id && p.principal_id !== userId)
        .map(
          (p) =>
            people.find((x) => x.principal_id === p.principal_id)?.label ||
            `member-${p.principal_id!.slice(0, 8)}`,
        );
    },
    [people, userId],
  );
  // `laneHasAgent` was DELETED here (2026-08-03). It existed so the sub-label
  // could say "N people · with Lisa" — singling one member out as the room's
  // real counterpart, which is the species assumption this pass removes. With
  // naming species-blind, no caller needs to ask what kind a participant is.
  // (`laneOtherHumans` survives above: the polling gate genuinely needs "is
  // another HUMAN here", because only a human's turns arrive out-of-band.)
  //
  // EVERY participant but the viewer, in cast order, species-blind (ADR-495 D1
  // + ADR-405 §5). This is the list a conventional messaging app names a room
  // from: it does not ask what KIND each member is, only who is present.
  //
  // THE DEFECT THIS FIXES (operator-observed 2026-08-03): naming used to run
  // `laneOtherHumans` first and fall through to "the lane's Agent" when there
  // were no other humans. A cast of {you, Lisa, Thinker} therefore rendered as
  // "Lisa · Critic · GPT-5" — one participant promoted to be the room's whole
  // identity, and the other silently dropped. A group of three read as a 1:1
  // with a spec sheet. That fall-through was species law: humans made a group,
  // Agents made a counterpart.
  const laneOthers = useCallback(
    (lane: { agent?: string | null; model: string; participants?: Participant[] }) => {
      const cast = lane.participants ?? [];
      const out = cast
        .filter((p) => !(p.member_kind === 'human' && p.principal_id === userId))
        .map((p) =>
          p.member_kind === 'agent'
            ? data?.agents?.find((a) => a.slug === p.agent_slug)?.name ||
              p.agent_slug ||
              'agent'
            : people.find((x) => x.principal_id === p.principal_id)?.label ||
              `member-${(p.principal_id || '').slice(0, 8)}`,
        );
      if (out.length) return out;
      // Pre-cast lanes (Studio/derive, pre-registry) have no participant rows:
      // their Agent — or failing that their engine — IS the counterpart.
      const a = laneAgent(lane);
      return a?.name ? [a.name] : [modelLabel(lane.model)];
    },
    [data, people, userId, laneAgent, modelLabel],
  );
  const laneLabel = useCallback(
    (lane: { agent?: string | null; model: string; participants?: Participant[] }) =>
      // One rule at every cast size: the room is named by who is in it.
      laneOthers(lane).join(', '),
    [laneOthers],
  );
  // WHO IS WORKING — one speaker, never the room (ADR-495 D3: "addressing
  // selects which ONE answers"; ADR-558 D3: "one authority for the responder").
  //
  // THE DEFECT THIS FIXES (operator-observed 2026-08-13): the indicator was
  // passed `laneLabel` — the comma-joined ROOM name — so a cast of {you,
  // Thinker, Lisa} rendered "Thinker, Lisa is working…" for a single reply.
  // Two names, one spinner, one answer: it read as though both Agents were
  // responding, which no ADR permits. `laneLabel` is right for the HEADER (the
  // room IS named by who is in it) and wrong for the speaker — the same string
  // answering two different questions.
  //
  // Undefined when the speaker is not knowable ahead of the turn (several
  // Agents, none addressed yet); LanePanel then falls back to the engine label,
  // which is honest rather than a guess at which face will answer.
  const laneSpeaker = useCallback(
    (lane: { agent?: string | null; model: string; participants?: Participant[] }) => {
      const agents = (lane.participants ?? []).filter((p) => p.member_kind === 'agent');
      if (agents.length === 1) {
        return (
          data?.agents?.find((a) => a.slug === agents[0].agent_slug)?.name ||
          agents[0].agent_slug ||
          undefined
        );
      }
      // Pre-cast (Studio/derive) lanes carry a resident; a multi-Agent cast has
      // no single knowable speaker until the turn resolves.
      return agents.length ? undefined : laneAgent(lane)?.name;
    },
    [data, laneAgent],
  );
  // The row's picture, from the SAME source as its name (ADR-558). A single
  // joined colleague lends their avatar; anything else (a group, a person, an
  // engine-only chat) has no one face, and AgentFace falls back to an initial.
  const laneAvatarUrl = useCallback(
    (lane: { agent?: string | null; participants?: Participant[] }) => {
      const agents = (lane.participants ?? []).filter((p) => p.member_kind === 'agent');
      if (agents.length === 1) {
        return data?.agents?.find((a) => a.slug === agents[0].agent_slug)?.avatar_url;
      }
      // Pre-cast (Studio/derive) lanes have no participant rows — their
      // resident is the counterpart.
      return agents.length ? undefined : laneAgent(lane)?.avatar_url;
    },
    [data, laneAgent],
  );
  // How many are in this conversation — EVERY participant, species-blind. The
  // ONE count; the header chip and the sub-label both read it, so they can
  // never disagree (the shipped pair did: the chip counted the whole cast
  // while the sub-label counted humans+1).
  const laneMemberCount = useCallback(
    (lane: { agent?: string | null; model: string; participants?: Participant[] }) =>
      lane.participants?.length ?? laneOthers(lane).length + 1,
    [laneOthers],
  );
  // THE ENGINE THAT WILL ACTUALLY ANSWER — the FE's mirror of the server's
  // responder rule (`routes/lanes.py::lane_turn`), and the fix for a surface
  // that told a member two different engines at once.
  //
  // THE DEFECT THIS REMOVES (observed 2026-08-13, operator screenshot): the
  // header read `Lisa · Critic · GPT-5` while the empty state read
  // `New chat · Gemini Flash`. Both were honest about their own source — the
  // header from the CAST agent's registry row, the body from `lane_meta.model`
  // — and both were true: Lisa runs on GPT-5, the lane was born on the
  // member's sticky engine. Two truths, one screen, no way to tell which one
  // answers.
  //
  // The server already decides this, and it decides for the RESPONDER: when
  // the cast names a colleague other than the lane's own, the turn re-points
  // the model to that colleague's. So the lane's birth engine is NOT what runs
  // — it is a historical fact about an empty transcript, and showing it as the
  // present tense is the lie. One source, mirrored once, read everywhere.
  //
  // ⚠️ This does NOT re-point `lane.model`. That field stays the ledger's
  // record of what the lane was created on (ADR-460 spec §6: deriving it at
  // turn time would let a registry edit retroactively relabel past turns).
  // This resolves a DISPLAY question — who answers next — and nothing else.
  const laneEngineLabel = useCallback(
    (lane: { agent?: string | null; model: string; participants?: Participant[] }) => {
      const responder = (lane.participants ?? []).find((p) => p.member_kind === 'agent');
      const a = responder
        ? data?.agents?.find((x) => x.slug === responder.agent_slug)
        : laneAgent(lane);
      return a?.engine || modelLabel(lane.model);
    },
    [data, laneAgent, modelLabel],
  );
  // The engine's MODEL ID, for the brand mark (ADR-558 D5 — an engine-first
  // surface says whose engine it is). Resolved from the LABEL above rather
  // than from an agent field, and that is deliberate: `list_agents` serves
  // `engine` (a label) and withholds `model` on purpose — the chooser must
  // never be handed an engine id (ADR-460 D4). So the icon is derived from the
  // same label the words use, which is what keeps them from ever disagreeing.
  // A label with no matching row falls back to the lane's own model, so a
  // brand mark is never invented for an engine we cannot name.
  const laneEngineModel = useCallback(
    (lane: { agent?: string | null; model: string; participants?: Participant[] }) => {
      const label = laneEngineLabel(lane);
      return data?.models.find((m) => m.label === label)?.id || lane.model;
    },
    [data, laneEngineLabel],
  );
  // The second line: a group says its size; a 1:1 says what the counterpart is
  // (`role · engine` for an Agent — ADR-463 §3, the technical fact stays
  // visible but is never the headline).
  const laneSubLabel = useCallback(
    (lane: { agent?: string | null; model: string; participants?: Participant[] }) => {
      // A GROUP (3+ in the cast, any mix) says its size and nothing else. It
      // used to say "3 people · with Lisa", which was wrong twice: "people" for
      // a cast that is mostly Agents, and one member singled out as the room's
      // real counterpart. `laneMemberCount` is the single count both this and
      // the header chip read.
      const n = laneMemberCount(lane);
      if (n > 2) return `${n} members`;
      // A 1:1 names WHAT the counterpart is — for an Agent that is its role +
      // engine (ADR-463 §3: the technical fact stays visible, just not as the
      // headline); for a person there is nothing to spec, so it says the shape
      // of the conversation instead. Both are "what is this thing I'm talking
      // to", asked once, answered per counterpart.
      const others = (lane.participants ?? []).filter(
        (p) => !(p.member_kind === 'human' && p.principal_id === userId),
      );
      if (others.length === 1 && others[0].member_kind === 'human') return 'Direct chat';
      // ADR-558: the counterpart is read from the CAST, not from `lane.agent`.
      // A colleague JOINS a conversation, so a lane whose cast holds one names
      // that colleague — `role · engine`, the ADR-463 §3 shape (the technical
      // fact stays visible, never the headline).
      const joined = others.length === 1 && others[0].member_kind === 'agent'
        ? data?.agents?.find((x) => x.slug === others[0].agent_slug)
        : null;
      // …and a lane with nobody else in it IS its engine. That is the ADR-558
      // default state of every new chat, so it is the honest label, not a gap:
      // the member picked an engine and nobody has joined yet.
      const a = joined || laneAgent(lane);
      // The engine half comes from the ONE resolver (`laneEngineLabel`), never
      // re-derived here — that duplicate derivation is what let the header and
      // the empty state disagree in the first place.
      if (!a) return laneEngineLabel(lane);
      return [a.kernel === false ? a.role : null, laneEngineLabel(lane)]
        .filter(Boolean)
        .join(' · ');
    },
    [data, laneAgent, laneEngineLabel, laneMemberCount, userId],
  );

  // Flat recents — pinned first (Phase-A hygiene), then updated_at desc
  // (falls back to created_at). Work-first: the sort key is activity, never
  // the model (D4).
  const lanes = useMemo(() => {
    const all = [...(data?.lanes ?? [])].sort((a, b) => {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      const ta = new Date(a.updated_at ?? a.created_at ?? 0).getTime();
      const tb = new Date(b.updated_at ?? b.created_at ?? 0).getTime();
      return tb - ta;
    });
    const byModel = whoFilter
      ? all.filter((l) => laneLabel(l) === whoFilter)
      : all;
    const q = query.trim().toLowerCase();
    if (!q) return byModel;
    return byModel.filter(
      (l) => l.name.toLowerCase().includes(q) || contentHits?.has(l.id),
    );
  }, [data, whoFilter, query, contentHits, laneLabel]);

  // The facet only offers colleagues actually present in the list.
  const presentWho = useMemo(
    () => Array.from(new Set((data?.lanes ?? []).map((l) => laneLabel(l)))),
    [data, laneLabel],
  );

  const activeLane = useMemo(
    () => (data?.lanes ?? []).find((l) => l.id === activeLaneId) ?? null,
    [data, activeLaneId],
  );

  // §6.10a — WHO the open conversation is with. Null for pre-registry and
  // Studio/derive lanes, which fall back to their engine label (honest: that
  // IS what those lanes are).
  const activeAgent = useMemo(
    () => (activeLane ? laneAgent(activeLane) : null),
    [activeLane, laneAgent],
  );

  // The header's stacked faces, in cast order, viewer excluded (you know you're
  // here — every messaging app omits you from its own group avatar). Agents
  // carry their picture; people fall back to an initial, which is what
  // AgentFace already does when there's no avatar. Falls back to the lane's own
  // Agent for pre-cast (Studio/derive) lanes so the header is never faceless.
  const headerFaces = useMemo<HeaderFace[]>(() => {
    if (!activeLane) return [];
    const cast = activeLane.participants ?? [];
    const faces: HeaderFace[] = [];
    for (const p of cast) {
      if (p.member_kind === 'agent') {
        const a = data?.agents?.find((x) => x.slug === p.agent_slug);
        faces.push({ name: a?.name || p.agent_slug || 'agent', avatarUrl: a?.avatar_url });
      } else if (p.principal_id && p.principal_id !== userId) {
        faces.push({
          name:
            people.find((x) => x.principal_id === p.principal_id)?.label ||
            `member-${p.principal_id.slice(0, 8)}`,
        });
      }
    }
    if (!faces.length && activeAgent) {
      faces.push({ name: activeAgent.name, avatarUrl: activeAgent.avatar_url });
    }
    return faces;
  }, [activeLane, data, people, userId, activeAgent]);

  // ADR-450 D5: a derive-bound lane arrives with ONE starter chip — the
  // suggested ask in the member's words (click fills the composer, the member
  // sends — never auto-sent, the ADR-446 lesson). The recipe section on the
  // lane's turns does the heavy lifting; the chip is just the door handle.
  const deriveSuggestions = useMemo(() => {
    if (!activeLane?.derive_recipe || !activeLane?.derive_source) return undefined;
    const label =
      data?.recipes?.find((r) => r.slug === activeLane.derive_recipe)?.label ??
      activeLane.derive_recipe;
    const leaf = activeLane.derive_source.slice(activeLane.derive_source.lastIndexOf('/') + 1);
    return [`Learn from ${leaf} — create the ${label.toLowerCase()}.`];
  }, [activeLane, data]);

  // ADR-442 D5: locator honesty — the active lane is the surface's crumb
  // (`Chat › ‹lane›`; the strip's root-click returns to the lane list). The
  // in-body headers stay: they carry content state (the model chip), not
  // surface chrome (ADR-442 D3).
  useWindowCrumb(
    'chat',
    activeLane
      ? showDetail
        ? [
            // Two levels deep: the lane, then its details. Clicking the lane
            // crumb closes the drill-in (not the lane) — the crumb path IS the
            // navigation, so each level must return to exactly its own level.
            {
              label: activeLane.name,
              onClick: () => setParam({ detail: null }),
            },
            { label: 'Details' },
          ]
        : [
            {
              label: activeLane.name,
              // Leaving the lane clears the drill-in too — otherwise `detail`
              // survives in the URL and the NEXT lane opens straight into its
              // participants list. A launch restores postures, never drill-ins
              // (the shell lesson: remembered state with no clearing path).
              onClick: () => setParam({ lane: null, detail: null }),
            },
          ]
      : [],
  );
  // 2026-07-14 (operator ruling): Chat renders its OWN locator in-body — the
  // always-visible lane-list column names "Chat" + every lane (it IS the
  // navigator), and the conversation header names the active lane + model. So
  // the OS surface bar suppresses for Chat — one "you are here", never two, and
  // the ~28px band is reclaimed.
  //
  // 2026-07-21: that ruling holds only while the lane list is ACTUALLY visible.
  // Under the one-screen collapse below, a drilled-in mobile lane hides the
  // list — the in-body locator that justified the suppression is off-screen,
  // and suppressing the OS strip there would strand the member with no way
  // back. So self-location is viewport-conditional: desktop (both columns, the
  // list IS the navigator) suppresses; drilled-in mobile yields to the OS
  // strip's `‹ {lane}` back chip. Same conditional shape Studio already uses.
  //
  // 2026-07-30: the participants drill-in is a THIRD level, and it hides the
  // in-body conversation header that would otherwise say where you are. It
  // renders its own back chip, but the OS strip carries the full crumb path
  // (Chat › ‹lane› › Details), so yield to it whenever the drill-in is open —
  // on any width, since the drill-in owns the whole pane at every size.
  useSelfLocatedSurface('chat', !((isNarrow && activeLane) || showDetail));

  // ADR-558 D1 — ONE create path, and it sends an ENGINE. The two paths this
  // replaces (`createLane(agentSlug)` and `createConversationWithPerson`) were
  // the same act wearing two different first questions; the server now refuses
  // `agent` on an unbound lane, so there is nothing to keep. Adding a colleague
  // or a teammate is the CAST's job, done from inside the conversation.
  //
  // No name: a lane auto-names from its first message (Phase-A hygiene).
  const createLane = useCallback(async (engineId: string) => {
    if (!engineId) return;
    try {
      const lane = await api.lanes.create({ model: engineId });
      const info: LaneInfo = {
        id: lane.id,
        name: lane.name,
        model: lane.model,
        updated_at: new Date().toISOString(),
      };
      setData((d) => (d ? { ...d, lanes: [...d.lanes, info] } : d));
      setParam({ lane: info.id, detail: null });
      setCreating(false);
    } catch (e) {
      // SHOW it. This swallowed a live 409 ("Lane limit reached") and the
      // member saw a click that did nothing, with no reason given. The modal
      // renders what we throw.
      throw e instanceof Error ? e : new Error('Could not start this chat');
    }
  }, [setParam]);

  const archiveLane = useCallback(
    async (laneId: string) => {
      try {
        await api.lanes.archive(laneId);
        setData((d) =>
          d ? { ...d, lanes: d.lanes.filter((l) => l.id !== laneId) } : d,
        );
        if (activeLaneId === laneId) setParam({ lane: null, detail: null });
      } catch {}
    },
    [activeLaneId, setParam],
  );

  // Phase-A hygiene: pin toggle + rename (lane_meta writes via PATCH).
  const updateLaneLocal = useCallback((laneId: string, patch: Partial<LaneInfo>) => {
    setData((d) =>
      d
        ? { ...d, lanes: d.lanes.map((l) => (l.id === laneId ? { ...l, ...patch } : l)) }
        : d,
    );
  }, []);

  const togglePin = useCallback(
    async (lane: LaneInfo) => {
      const next = !lane.pinned;
      updateLaneLocal(lane.id, { pinned: next });
      try {
        await api.lanes.patch(lane.id, { pinned: next });
      } catch {
        updateLaneLocal(lane.id, { pinned: lane.pinned });
      }
    },
    [updateLaneLocal],
  );

  const commitRename = useCallback(async () => {
    const laneId = renamingId;
    const name = renameText.trim();
    setRenamingId(null);
    if (!laneId || !name) return;
    const prev = data?.lanes.find((l) => l.id === laneId)?.name;
    updateLaneLocal(laneId, { name });
    try {
      await api.lanes.patch(laneId, { name });
    } catch {
      if (prev) updateLaneLocal(laneId, { name: prev });
    }
  }, [renamingId, renameText, data, updateLaneLocal]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  // Router off — lanes have no engine (ADR-411 D2 gate). Honest state, no
  // dead affordances.
  if (!data?.enabled) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="max-w-sm text-center space-y-2 text-sm text-muted-foreground">
          <MessageCircle className="w-6 h-6 mx-auto text-muted-foreground/50" />
          <p className="font-medium text-foreground/80">Chat is not enabled</p>
          {/* §6.10b — this used to name the routing module by its internal
              name and report that it wasn't live: a module name shown to a
              member, asking them to care about an engine. */}
          <p>
            Chat colleagues aren&apos;t available on this deployment yet. Your
            conversation with Freddie is unaffected — summon it from the chat
            button.
          </p>
        </div>
      </div>
    );
  }

  // The new-chat flow is a MODAL (NewChatModal) — ADR-558 D1: it asks WHICH
  // ENGINE. People and colleagues join through the CAST, from inside the
  // conversation, which is why neither is passed here any more.

  return (
    <div ref={surfaceRef} className="h-full flex min-h-0">
      {creating && (
        <NewChatModal
          engines={data?.models ?? []}
          onPick={createLane}
          onClose={() => setCreating(false)}
        />
      )}
      {/* Lane list — flat recents, work-first (D4). On mobile it's the whole
          screen (w-full) and yields entirely once a lane is picked; on desktop
          it's the fixed 288px navigator column that's always present. */}
      <div
        className={cn(
          'flex-col min-h-0',
          // The divider is a two-column artifact — full-width it's a hairline
          // against the screen edge.
          isNarrow ? 'w-full' : 'w-72 shrink-0 flex border-r border-border',
          isNarrow && (activeLane ? 'hidden' : 'flex'),
        )}
      >
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-border shrink-0">
          <span className="text-sm font-medium">Chat</span>
          <button
            onClick={() => setCreating((v) => !v)}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            aria-label="New lane"
            title="New lane"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Phase-A hygiene: search — lane names locally + transcript content
            server-side (debounced), one filter over the same list. */}
        <div className="px-2 py-1.5 border-b border-border shrink-0">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/60" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setQuery('');
              }}
              placeholder="Search chats…"
              className="w-full rounded border border-input bg-background pl-7 pr-6 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5 rounded text-muted-foreground hover:text-foreground"
                aria-label="Clear search"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* The filter facet — by WHO, on demand, never the default grouping
            (D4). Renders only when ≥2 colleagues are in play. */}
        {presentWho.length > 1 && (
          <div className="flex items-center gap-1 px-2 py-1.5 border-b border-border shrink-0 overflow-x-auto">
            <button
              onClick={() => setWhoFilter(null)}
              className={cn(
                'px-2 py-0.5 rounded-full text-[11px] whitespace-nowrap transition-colors',
                whoFilter === null
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground',
              )}
            >
              All
            </button>
            {presentWho.map((m) => (
              <button
                key={m}
                onClick={() => setWhoFilter((cur) => (cur === m ? null : m))}
                className={cn(
                  'px-2 py-0.5 rounded-full text-[11px] whitespace-nowrap transition-colors',
                  whoFilter === m
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:text-foreground',
                )}
              >
                {m}
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 min-h-0 overflow-y-auto">
          {lanes.length === 0 && (
            <div className="px-4 py-8 text-center text-xs text-muted-foreground space-y-1.5">
              <p className="font-medium text-foreground/80">No chats yet</p>
              {/* §6.10b — this used to open "a lane is a conversation pinned
                  to a MODEL OF YOUR CHOICE", which is the one question
                  ADR-460 D1 says a member must never be asked. The ADR-411
                  contract it carries (isolation · shared files · attribution)
                  is preserved — only the frame moves from engine to
                  colleague. */}
              <p>
                Each chat is a conversation with one colleague, kept separate
                from the others. Your workspace files are the shared memory —
                whatever a colleague makes lands there, attributed to you.
              </p>
            </div>
          )}
          {lanes.length === 0 && query.trim() && (
            <div className="px-4 py-6 text-center text-xs text-muted-foreground">
              No chats match “{query.trim()}”.
            </div>
          )}
          {lanes.map((lane) =>
            renamingId === lane.id ? (
              // Rename mode replaces the row — an input can't nest inside the
              // row <button> (invalid interactive nesting).
              <div
                key={lane.id}
                className="px-3 py-2.5 border-b border-border/50 bg-muted"
              >
                <input
                  value={renameText}
                  onChange={(e) => setRenameText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void commitRename();
                    if (e.key === 'Escape') setRenamingId(null);
                  }}
                  onBlur={() => void commitRename()}
                  className="w-full rounded border border-input bg-background px-1.5 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  autoFocus
                />
              </div>
            ) : (
            <button
              key={lane.id}
              onClick={() => setParam({ lane: lane.id, detail: null })}
              className={cn(
                'w-full text-left px-3 py-2.5 border-b border-border/50 transition-colors group',
                'flex items-start gap-2.5',
                activeLaneId === lane.id ? 'bg-muted' : 'hover:bg-muted/50',
              )}
            >
              {/* The row leads with a face. `laneLabel` already names the room
                  from its CAST; the avatar follows the same source (ADR-558 —
                  `lane.agent` is a bound lane's resident and is null on every
                  chat conversation, so keying the picture on it left a joined
                  colleague's avatar blank while their NAME rendered). */}
              <AgentFace
                name={laneLabel(lane)}
                avatarUrl={laneAvatarUrl(lane)}
                size="md"
                className="mt-0.5"
              />
              <span className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1">
                <span className="text-sm font-medium truncate flex items-center gap-1">
                  {lane.pinned && (
                    <Pin className="w-3 h-3 shrink-0 text-muted-foreground rotate-45" />
                  )}
                  {lane.name}
                </span>
                {/* Phase-A hygiene: pin / rename / archive on hover. */}
                <span className="flex items-center shrink-0">
                  <span
                    role="button"
                    tabIndex={-1}
                    onClick={(e) => {
                      e.stopPropagation();
                      void togglePin(lane);
                    }}
                    className={cn(
                      'p-1 rounded transition-colors hover:!text-foreground',
                      lane.pinned
                        ? 'text-muted-foreground'
                        : 'text-muted-foreground/0 group-hover:text-muted-foreground',
                    )}
                    aria-label={lane.pinned ? 'Unpin lane' : 'Pin lane'}
                    title={lane.pinned ? 'Unpin' : 'Pin'}
                  >
                    <Pin className={cn('w-3.5 h-3.5', lane.pinned && 'rotate-45')} />
                  </span>
                  <span
                    role="button"
                    tabIndex={-1}
                    onClick={(e) => {
                      e.stopPropagation();
                      setRenamingId(lane.id);
                      setRenameText(lane.name);
                    }}
                    className="p-1 rounded text-muted-foreground/0 group-hover:text-muted-foreground hover:!text-foreground transition-colors"
                    aria-label="Rename lane"
                    title="Rename"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </span>
                  <span
                    role="button"
                    tabIndex={-1}
                    onClick={(e) => {
                      e.stopPropagation();
                      void archiveLane(lane.id);
                    }}
                    className="p-1 rounded text-muted-foreground/0 group-hover:text-muted-foreground hover:!text-foreground transition-colors"
                    aria-label="Archive lane"
                    title="Archive lane"
                  >
                    <Archive className="w-3.5 h-3.5" />
                  </span>
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                {/* The colleague, then the technical fact — "Lisa · Critic ·
                    GPT-5". The operator's rule: a nickname must still say what
                    it IS (at minimum the role + the model). Identity leads; the
                    spec rides quietly behind it. */}
                <span className="text-[11px] text-foreground/70 truncate">
                  {laneLabel(lane)}
                </span>
                {/* ADR-558 D5 — an engine-first surface says WHOSE engine it
                    is. Keyed on the engine that will ANSWER (laneEngineModel),
                    the same resolution the words use, so the mark and the label
                    can never name different providers. */}
                <span className="shrink-0 text-muted-foreground/70 [&>svg]:w-3 [&>svg]:h-3">
                  {engineBrandIcon(laneEngineModel(lane))}
                </span>
                <span className="text-[10px] text-muted-foreground/70 truncate">
                  {laneSubLabel(lane)}
                </span>
                {(lane.updated_at ?? lane.created_at) && (
                  <span className="text-[10px] text-muted-foreground/60">
                    {formatRelativeTime(lane.updated_at ?? lane.created_at!)}
                  </span>
                )}
              </div>
              </span>
            </button>
            ),
          )}
        </div>
      </div>

      {/* Conversation area. On mobile it takes the whole screen when a lane is
          open and is absent otherwise — its empty state ("pick a lane on the
          left") is a desktop sentence; on one screen the lane list already IS
          that instruction. */}
      <div
        className={cn(
          'flex-1 min-w-0 flex-col min-h-0',
          isNarrow && !activeLane ? 'hidden' : 'flex',
        )}
      >
        {activeLane && showDetail && !activeLane.derive_recipe ? (
          /* The participants drill-in OWNS the pane while open — one screen at a
             time, on every width (ADR-297 D15). A side-by-side split would put
             the cast back in competition with the transcript, which is the
             crowding this refactor removed. */
          <ConversationDetail
            key={`detail-${activeLane.id}`}
            laneId={activeLane.id}
            laneName={activeLane.name}
            agents={data?.agents ?? []}
            people={people}
            viewerId={userId}
            initialParticipants={activeLane.participants}
            // `detail=add` lands with the invite already open — the header's
            // Add is one gesture to the act, not one gesture to a roster the
            // member then has to find the invite inside of.
            startAdding={detailParam === 'add'}
            onBack={() => setParam({ detail: null })}
            onCastChanged={(participants) =>
              updateLaneLocal(activeLane.id, { participants })
            }
          />
        ) : activeLane ? (
          <>
            {/* ONE header row, conventional grammar (see ConversationHeader):
                stacked faces · title · participant count · ⋯ → details.

                The four-jobs-in-one-row header this replaces (identity + lane
                name + the whole cast as chips + an actions portal) wrapped at
                three participants and was unusable on a phone. The cast now
                lives behind ⋯, which is where every messaging app puts it and
                the only shape that survives N participants.

                People lead whenever there are people — including the mixed
                cast, which the old header could not express (it branched
                agent-OR-humans, never both). */}
            <ConversationHeader
              key={`header-${activeLane.id}`}
              title={laneLabel(activeLane)}
              subtitle={laneSubLabel(activeLane)}
              // ADR-558 D5 — the mark, only where a single engine is the
              // answer. A group's sub-label says its SIZE, so there is no one
              // engine to attribute and a mark there would claim a fact the
              // words do not make.
              engineModel={
                laneMemberCount(activeLane) <= 2 ? laneEngineModel(activeLane) : null
              }
              faces={headerFaces}
              participantCount={laneMemberCount(activeLane)}
              // The faces link to a card only when a SINGLE Agent is the whole
              // counterpart. In a group — any mix — there is no one card that
              // describes the room, so they open the details instead.
              //
              // ADR-558: read the counterpart from the CAST first. A colleague
              // JOINS now, so `lane.agent` (the bound-lane resident) is null on
              // every chat conversation — keying only on it meant a joined
              // colleague's face linked nowhere.
              agentSlug={
                laneMemberCount(activeLane) <= 2
                  ? (activeLane.participants ?? []).find(
                      (p) => p.member_kind === 'agent',
                    )?.agent_slug ?? activeAgent?.slug ?? null
                  : null
              }
              onOpenDetails={() => setParam({ detail: 'participants' })}
              // The dedicated invite act: straight to the add flow, not to the
              // roster with the invite hidden inside it.
              onAddParticipant={() => setParam({ detail: 'add' })}
            />
            <LanePanel
              key={activeLane.id}
              laneId={activeLane.id}
              laneName={activeLane.name}
              // The engine that will ANSWER, not the one the lane was born on
              // (`laneEngineLabel`). The birth engine is a ledger fact about an
              // empty transcript; showing it as the present tense is what made
              // the header and the body name two different engines.
              modelLabel={laneEngineLabel(activeLane)}
              // ADR-562 D5 — WHO is working. The prop existed and was never
              // passed here, so the panel fell back to the engine label and a
              // conversation with Lisa introduced itself as an engine. Passing
              // `laneLabel` fixed that but overshot: it is the ROOM's name, so
              // a 3-member cast read "Thinker, Lisa is working…" for one reply.
              // One speaker, or none — never the roster (2026-08-13).
              speakerLabel={laneSpeaker(activeLane)}
              // Freshness follows the PEOPLE, not the absence of an Agent
              // (audited 2026-07-30). This was `laneOtherHumans(...).length > 0`
              // back when that helper returned [] whenever an Agent was in the
              // cast — so a 3-person chat with an Agent got NO polling and the
              // others' messages never arrived until remount. Any conversation
              // with another human needs out-of-band refresh, because their
              // turns don't ride the asker's stream.
              hasOtherHumans={laneOtherHumans(activeLane).length > 0}
              viewerId={userId}
              principalLabels={Object.fromEntries(
                people.map((p) => [p.principal_id, p.label]),
              )}
              suggestions={deriveSuggestions}
              // Phase-A hygiene: the first turn auto-names a default-named
              // lane server-side; reflect it in the list + header.
              onLaneRenamed={(name) => updateLaneLocal(activeLane.id, { name })}
              // Phase-A attachments: gate the image affordance on the lane
              // model's vision flag (the server guards regardless).
              visionCapable={
                data.models.find((m) => m.id === activeLane.model)?.vision ?? true
              }
              // ADR-514 D2.3 — "Open With → Chat" hands the cited paths here.
              // Space-separated because a reference is naturally plural (a
              // multi-selection or a folder); the composer binds each one.
              citePaths={citePaths}
              onCiteConsumed={() => setParam({ cite: null })}
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="max-w-sm text-center space-y-2 text-sm text-muted-foreground">
              <MessageCircle className="w-6 h-6 mx-auto text-muted-foreground/50" />
              <p className="font-medium text-foreground/80">
                Your conversations
              </p>
              {/* §6.10b — same re-frame as the two empty states above: a
                  chat is with a COLLEAGUE, not with a chosen engine. */}
              <p>
                Each chat is with one colleague, kept separate from the
                others; your workspace files are the shared memory. Pick a
                chat on the left or start a new one — the work lands in your
                files, attributed to you.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
