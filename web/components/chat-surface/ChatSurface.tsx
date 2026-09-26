'use client';

/**
 * ChatSurface — the chat workbench (ADR-412 D3/D4).
 *
 * Your conversations with colleagues (ADR-411 lanes) as a windowed surface —
 * a working area summoned like any window, distinct from the Agents roster
 * (who they are).
 *
 * ADR-670 D2 — the frame is PANES' own, and nothing new: the lane list is the
 * INDEX (rail: what needs you · who · the list), the conversation is the
 * OBJECT (canvas), and what the conversation made and ran is the SUPERVISION
 * beside it (side). The ladder folds the side: an overlay at `two-pane`, a
 * bottom tab at `single-pane`.
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
 * named by its work with the pinned model as a CHIP; a WHO filter gives the
 * by-agent view on demand (ADR-460 re-axed it from the engine; ADR-670 D4
 * made it the agents' faces). Model-first folders are rejected (ADR-385
 * precedent: group by relationship, never transport).
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
import { useTranslations } from 'next-intl';
import { Archive, MessageCircle, PanelLeft, PanelRight, Pencil, Pin, Plus, Search, X } from 'lucide-react';
import { Working } from '@/components/shared/Working';
import { LanePanel, type MadeHereFile } from './LanePanel';
import { ChatSupervision } from './ChatSupervision';
import { NeedsYouStrip, WhoStrip } from './ChatIndexStrips';
import { ConversationHeader, type HeaderFace } from './ConversationHeader';
import { ConversationDetail } from './ConversationDetail';
import { AgentFace } from '@/components/agents/AgentFace';
import type { PrincipalKind } from '@/lib/workspace/attribution';
import { NewChatModal } from './NewChatModal';
import { useWorkspaceMembers } from '@/lib/workspace/viewer';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { api, type Participant } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';
import { engineBrandIcon } from '@/lib/ai-providers/brand-icons';
import { cn } from '@/lib/utils';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { slotIsColumn, usePaneLadder, usePaneSlot } from '@/lib/shell/pane-layout';
import { useSelfLocatedSurface, useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { useFeedback } from '@/contexts/FeedbackContext';
import { isSubmitKey } from '@/lib/shell/submit-key';

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
  /** ADR-450 D3 / ADR-630 — the skill binding (null/absent for plain chat lanes). */
  skill?: string | null;
  derive_source?: string | null;
  /** ADR-495 D1 — the cast, seeded from the list so the bar paints at once. */
  participants?: Participant[];
}

interface LaneData {
  enabled: boolean;
  /** ADR-601 D4 / ADR-614 D1 / ADR-631 — every agent that EXISTS, with
   *  provenance and the apps it works in. ONE roster: `offered` rides each row.
   *  This is what the new-chat door lists and what every naming site reads. */
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
  /** The CHOOSER — the OFFERED roster only (retired engines leave the door,
   *  ADR-559 D2). ⚠️ This comment used to claim "every model stays routable"
   *  is served here; it is not, and reading it that way is what let a lane on a
   *  retired engine render its raw id. For NAMING an engine use `model_names`. */
  models: Array<{ id: string; label: string; vision?: boolean;
          /** ADR-559 D3 — false when the engine cannot run right now.
           *  Served (not filtered) so the door can grey it WITH a reason. */
          available?: boolean; unavailable_reason?: string | null;
          /** ADR-647 D8 — the provider's own words for a refusal, when we have
           *  them, so a greyed row says WHICH kind of dark it is. */
          unavailable_detail?: string | null }>;
  /** ADR-647 D4 — the member's standing engine preference for this workspace,
   *  resolved server-side (so a stale value reads as null rather than marking
   *  an engine the door would refuse). Null = no preference. */
  default_engine?: string | null;
  /** id → label for EVERY engine, retired included. The NAMING table (see
   *  `modelLabel`). Optional so an older envelope degrades, never crashes. */
  model_names?: Record<string, string>;
  /** ADR-450 D5 / ADR-630 — yarnnn's skills (the Learn-from chooser payload). */
  skills?: Array<{ slug: string; title: string; description: string; path: string }>;
  lanes: LaneInfo[];
}

export function ChatSurface() {
  const t = useTranslations('chat');
  const [data, setData] = useState<LaneData | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  // D4 — the FILTER (null = all lanes, the default view). ADR-460: it
  // filters by WHO you talked to, not by which engine ran. ADR-670 D4 — the
  // filter is made VISIBLE as the agents' faces (the Who strip): it holds an
  // agent's slug, and a chat matches when that agent is in it. One state; the
  // strip renders it and asks to change it.
  const [whoFilter, setWhoFilter] = useState<string | null>(null);
  // ADR-670 D3 — what this conversation made, reported UP by the panel (which
  // holds the transcript), the same way `defaultResponder` is.
  const [madeHere, setMadeHere] = useState<MadeHereFile[]>([]);
  // At the single-pane rung the conversation and its supervision are two tabs
  // of one screen; above it they sit side by side and this is unused.
  const [narrowPane, setNarrowPane] = useState<'conversation' | 'side'>('conversation');
  // WHO answers an unaddressed message — reported UP by the panel (which holds
  // the transcript) so the Details roster can mark it. One derivation, two
  // readers; deriving it again here would be free to disagree with the panel.
  const [defaultResponder, setDefaultResponder] = useState<string | null>(null);
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
  const { runAction } = useFeedback();
  const { members: wsMembers } = useWorkspaceMembers();
  // The workspace's other humans — invitable into any conversation (ADR-495
  // D3: one species-blind invite; a person is a participant like any other).
  const people = useMemo(
    () =>
      wsMembers
        .filter((m) => (m.role === 'owner' || m.role === 'member') && m.principal_id !== userId)
        .map((m) => ({ principal_id: m.principal_id, label: m.label || 'A member' })),
    [wsMembers, userId],
  );
  // Measured on THIS surface's own box, not the viewport — a surface can be
  // narrow inside a roomy window (a 320px window on a 1440px monitor), and a
  // 768px tablet reads "desktop" to the viewport whatever room the surface
  // itself was actually given.
  //
  // The rungs are the SHELL's (`lib/shell/pane-layout.ts`), not a threshold of
  // this surface's own. Chat previously hand-rolled 600px, which was a fourth
  // spelling of "how wide is wide" and disagreed with the three around it.
  const [setPaneNode, wb] = usePaneLadder();
  // Chat composes all three slots (ADR-670 D2): the RAIL is the index, the
  // CANVAS the conversation, the SIDE its supervision (what it made, what it
  // ran). The participants drill-in still takes the whole pane rather than
  // splitting it (see the ADR note at the detail mount below).
  const rail = usePaneSlot('chat', 'rail', userId, wb, { defaultShown: true });
  // The side rests shown where it is a COLUMN and withdrawn where it would be
  // an OVERLAY — an overlay covers the conversation, and a conversation the
  // member opened must not arrive covered. A moving default (PANES §5): it
  // follows the rung until the member chooses, and never fights them after.
  const side = usePaneSlot('chat', 'side', userId, wb, { defaultShown: !wb.sideIsOverlay });
  // One screen at a time at the narrowest rung: the lane list IS the screen
  // until you pick a lane, then the conversation is.
  const isNarrow = wb.singlePane;
  // The rail is a real COLUMN only above the narrowest rung and only while the
  // member is showing it. Derived once — branching on the pair at each call
  // site is how Studio and Text came to disagree about when a toggle exists.
  const railIsColumn = !isNarrow && rail.shown;
  const sideIsColumn = slotIsColumn(wb, side);

  // Escape withdraws the side while it is an OVERLAY (it covers the canvas, so
  // it is modal); a COLUMN is not, and Escape must not reach across and close
  // it. Studio's rule, the same slot.
  useEffect(() => {
    if (!wb.sideIsOverlay || !side.shown) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') side.toggle();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [wb.sideIsOverlay, side]);

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

  // NAMING, not choosing. `model_names` covers EVERY engine including retired
  // ones; `models` is the chooser and carries only the offered roster. A lane's
  // engine is persisted at creation and is a historical fact (ADR-460 D4), so a
  // lane on a retired engine has no `models` row — before 2026-08-21 it fell
  // through to the RAW ID and rendered `anthropic/claude-sonnet-4-6` as a filter
  // chip. `models` stays in the chain so an older envelope still names offered
  // engines; the raw id remains the last resort for a genuinely unknown one.
  const modelLabel = useCallback(
    (modelId: string) =>
      data?.model_names?.[modelId] ??
      data?.models.find((m) => m.id === modelId)?.label ??
      modelId,
    [data],
  );

  // ⭐ THE ONE PLACE A SLUG BECOMES A COLLEAGUE (2026-08-27, ADR-614 follow-up).
  //
  // THE DEFECT THIS CLOSES, operator-observed on the deployed surface: a chat
  // started with Editor rendered "Claude Sonnet 5" in the header and the list,
  // and the Details pane showed the raw slug `editor` under AGENTS. The cast
  // was CORRECT — the row said `editor`, and the turn was answered by Editor.
  // Only the NAMING was wrong, in ten places at once.
  //
  // The cause: every site resolved against `data.agents`, which is the INVITE
  // roster (`offered`) — and `offered` is FALSE for all three agents today
  // (ADR-599 D1/ADR-600), so that array is EMPTY and every lookup returned
  // undefined. The fallbacks then did exactly what they were written to do:
  // the header fell through to the engine label, the pane fell through to the
  // slug. Latent until now, because before ADR-614 a chat lane had no agent in
  // its cast and there was nothing to name.
  //
  // `agents` is the right table — every agent that EXISTS, not the subset a
  // member may invite (ADR-601 D4's whole reason for serving both). Resolved
  // through ONE function so a future roster question has one answer: ten call
  // sites reading a roster directly is how all ten were wrong together.
  const agentBySlug = useCallback(
    (slug?: string | null) =>
      (slug && data?.agents?.find((b) => b.slug === slug)) || null,
    [data],
  );

  // ADR-597 D1 — `lane.agent` is the lane's DERIVED resident (a bound lane's
  // app declares it; a chat lane started from the door has one too). Named
  // through the same resolver as every cast row, so a lane and its cast can
  // never disagree about what to call the same agent.
  const laneAgent = useCallback(
    (lane: { agent?: string | null }) => agentBySlug(lane.agent),
    [agentBySlug],
  );
  // Is this agent IN the conversation? Read from the CAST (a colleague joins,
  // ADR-558), falling back to the resident only for a pre-cast lane with no
  // agent rows — the same branch `laneAvatarUrl` takes, so the face a member
  // chose and the faces on the rows it keeps can never disagree.
  const laneIncludesAgent = useCallback(
    (lane: { agent?: string | null; participants?: Participant[] }, slug: string) => {
      const agents = (lane.participants ?? []).filter((p) => p.member_kind === 'agent');
      return agents.length
        ? agents.some((p) => p.agent_slug === slug)
        : lane.agent === slug;
    },
    [],
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
            'A member',
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
            ? agentBySlug(p.agent_slug)?.name || p.agent_slug || 'agent'
            : people.find((x) => x.principal_id === p.principal_id)?.label ||
              'A member',
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
          agentBySlug(agents[0].agent_slug)?.name ||
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
        return agentBySlug(agents[0].agent_slug)?.avatar_url;
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
        ? agentBySlug(responder.agent_slug)
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
      if (n > 2) return t('members', { count: n });
      // A 1:1 names WHAT the counterpart is — for an Agent that is its role +
      // engine (ADR-463 §3: the technical fact stays visible, just not as the
      // headline); for a person there is nothing to spec, so it says the shape
      // of the conversation instead. Both are "what is this thing I'm talking
      // to", asked once, answered per counterpart.
      const others = (lane.participants ?? []).filter(
        (p) => !(p.member_kind === 'human' && p.principal_id === userId),
      );
      if (others.length === 1 && others[0].member_kind === 'human') return t('directChat');
      // ADR-558: the counterpart is read from the CAST, not from `lane.agent`.
      // A colleague JOINS a conversation, so a lane whose cast holds one names
      // that colleague — `role · engine`, the ADR-463 §3 shape (the technical
      // fact stays visible, never the headline).
      const joined = others.length === 1 && others[0].member_kind === 'agent'
        ? agentBySlug(others[0].agent_slug)
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
    const byWho = whoFilter
      ? all.filter((l) => laneIncludesAgent(l, whoFilter))
      : all;
    const q = query.trim().toLowerCase();
    if (!q) return byWho;
    return byWho.filter(
      (l) => l.name.toLowerCase().includes(q) || contentHits?.has(l.id),
    );
  }, [data, whoFilter, query, contentHits, laneIncludesAgent]);

  // ADR-670 D4 — the Who strip's faces: every agent on the roster the list
  // already carries (`data.agents`, ADR-601 D4 — every agent that EXISTS). No
  // second roster read.
  const whoFaces = useMemo(
    () =>
      (data?.agents ?? []).map((a) => ({ slug: a.slug, name: a.name, avatarUrl: a.avatar_url })),
    [data],
  );

  const activeLane = useMemo(
    () => (data?.lanes ?? []).find((l) => l.id === activeLaneId) ?? null,
    [data, activeLaneId],
  );

  // The row's face KIND, from the SAME cast read as its name and picture
  // (ADR-641 amendment). A room led by exactly one agent wears the agent hue;
  // anything else — a group, a person, an engine-only chat — is a human room.
  // Deliberately mirrors `laneAvatarUrl`'s branch rather than inventing a
  // second rule: if the two ever disagree, the face and the name would be
  // describing different participants.
  const laneFaceKind = useCallback(
    (lane: { agent?: string | null; participants?: Participant[] }): PrincipalKind => {
      const agents = (lane.participants ?? []).filter((p) => p.member_kind === 'agent');
      if (agents.length === 1) return 'agent';
      if (agents.length) return 'human'; // a mixed/multi-agent group is a room
      return laneAgent(lane) ? 'agent' : 'human';
    },
    [laneAgent],
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
        const a = agentBySlug(p.agent_slug);
        faces.push({
          name: a?.name || p.agent_slug || 'agent',
          avatarUrl: a?.avatar_url,
          kind: 'agent',
        });
      } else if (p.principal_id && p.principal_id !== userId) {
        faces.push({
          name:
            people.find((x) => x.principal_id === p.principal_id)?.label ||
            'A member',
          kind: 'human',
        });
      }
    }
    if (!faces.length && activeAgent) {
      // The pre-cast (Studio/derive) fall-back — the lane's own resident, which
      // is an agent by construction.
      faces.push({ name: activeAgent.name, avatarUrl: activeAgent.avatar_url, kind: 'agent' });
    }
    return faces;
  }, [activeLane, data, people, userId, activeAgent]);

  // ADR-450 D5: a derive-bound lane arrives with ONE starter chip — the
  // suggested ask in the member's words (click fills the composer, the member
  // sends — never auto-sent, the ADR-446 lesson). The skill section on the
  // lane's turns does the heavy lifting; the chip is just the door handle.
  const deriveSuggestions = useMemo(() => {
    if (!activeLane?.skill || !activeLane?.derive_source) return undefined;
    const label =
      data?.skills?.find((r) => r.slug === activeLane.skill)?.title ??
      activeLane.skill;
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
      ? [
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
  // 2026-08-20 (operator ruling): the drill-in does NOT yield to the OS strip.
  // The 2026-07-30 exception above traded one problem for a worse one: the
  // strip is a shell-level sibling ABOVE the whole content row
  // (ShellCompositor), so un-suppressing it on the Details screen alone
  // inserted a full-width band that pushed the lane list down — the chrome
  // moved when only the right pane had changed. A locator that reflows the
  // layout it describes is a discontinuity, not a locator.
  //
  // It was also redundant three ways over: ConversationDetail renders its own
  // back arrow (`onBack` → `detail: null`, the exact act the 'Details' crumb
  // performed), names itself in its own header, and the lane list stays
  // visible on desktop with the active lane highlighted. Suppression is
  // therefore viewport-conditional ONLY — the mobile branch still yields,
  // because there the drilled-in lane genuinely hides the list.
  useSelfLocatedSurface('chat', !(isNarrow && activeLane));

  // ADR-614 D1 — ONE create path, and it sends WHO or WHICH ENGINE. It stays
  // one path: the door answers a single question with two kinds of answer, and
  // naming a colleague resolves to a cast row + their engine SERVER-side, so
  // the client assembles no persona and no model of its own. Inviting a
  // teammate remains the CAST's job, from inside the conversation (ADR-495).
  //
  // No name: a lane auto-names from its first message (Phase-A hygiene).
  const createLane = useCallback(async (choice: { agent?: string; model?: string }) => {
    if (!choice.agent && !choice.model) return;
    try {
      // ADR-614 D1 — the door sends WHO or WHICH ENGINE. Naming a colleague
      // seeds the cast server-side and resolves their engine there; the client
      // never names a model on the member's behalf, and never both.
      // The modal STAYS OPEN on failure and renders what we throw (the live
      // 409 "Lane limit reached" below), so the error keeps its in-surface
      // home — one failure, one channel. The wait is what was missing.
      const lane = await runAction(() => api.lanes.create(choice), {
        pending: t('starting'),
      });
      const info: LaneInfo = {
        id: lane.id,
        name: lane.name,
        model: lane.model,
        updated_at: new Date().toISOString(),
      };
      setData((d) => (d ? { ...d, lanes: [...d.lanes, info] } : d));
      setParam({ lane: info.id, detail: null });
      setCreating(false);
      return lane;
    } catch (e) {
      // SHOW it. This swallowed a live 409 ("Lane limit reached") and the
      // member saw a click that did nothing, with no reason given. The modal
      // renders what we throw.
      throw e instanceof Error ? e : new Error(t('errors.start'));
    }
  }, [setParam, runAction]);

  // The archive used to `catch {}`: the lane vanished from the list whether or
  // not the server archived it, so a failure looked exactly like a success and
  // the lane returned on the next load. The row is removed only AFTER the call
  // resolves, and a failure now says so.
  const archiveLane = useCallback(
    async (laneId: string) => {
      try {
        await runAction(() => api.lanes.archive(laneId), {
          pending: t('archiving'),
          success: t('archived'),
          error: t('errors.archive'),
        });
      } catch {
        return; // reported; the lane stays in the list, which is the truth
      }
      setData((d) => (d ? { ...d, lanes: d.lanes.filter((l) => l.id !== laneId) } : d));
      if (activeLaneId === laneId) setParam({ lane: null, detail: null });
    },
    [activeLaneId, setParam, runAction],
  );

  // Phase-A hygiene: pin toggle + rename (lane_meta writes via PATCH).
  const updateLaneLocal = useCallback((laneId: string, patch: Partial<LaneInfo>) => {
    setData((d) =>
      d
        ? { ...d, lanes: d.lanes.map((l) => (l.id === laneId ? { ...l, ...patch } : l)) }
        : d,
    );
  }, []);

  // ADR-670 D4 — a face was chosen in the Who strip. With a chat already, it
  // is the who-filter (choosing it again shows every chat); with none, it
  // starts one through the ONE create path above — the door's own act.
  const chooseWho = useCallback(
    (slug: string) => {
      if ((data?.lanes ?? []).some((l) => laneIncludesAgent(l, slug))) {
        setWhoFilter((cur) => (cur === slug ? null : slug));
        return;
      }
      setWhoFilter(null);
      // The server seeds the chosen colleague into the cast and says so
      // (`lane.agent`); the row carries it until the next list read brings the
      // cast, so choosing the same face again filters rather than starting a
      // second chat. A failure is already reported by runAction's toast.
      void createLane({ agent: slug })
        .then((lane) => lane && updateLaneLocal(lane.id, { agent: lane.agent ?? slug }))
        .catch(() => undefined);
    },
    [data, laneIncludesAgent, createLane, updateLaneLocal],
  );

  // A lane switch starts on the conversation, never on the previous lane's
  // side tab (single-pane only).
  useEffect(() => {
    setNarrowPane('conversation');
  }, [activeLaneId]);

  const togglePin = useCallback(
    async (lane: LaneInfo) => {
      const next = !lane.pinned;
      updateLaneLocal(lane.id, { pinned: next });
      try {
        // Optimistic, so no `pending` — the pin already moved. The revert is
        // what needs the words: without them the pin silently flips back and
        // the member reads it as the app ignoring the click.
        await runAction(() => api.lanes.patch(lane.id, { pinned: next }), {
          error: next ? t('errors.pin') : t('errors.unpin'),
        });
      } catch {
        updateLaneLocal(lane.id, { pinned: lane.pinned });
      }
    },
    [updateLaneLocal, runAction],
  );

  const commitRename = useCallback(async () => {
    const laneId = renamingId;
    const name = renameText.trim();
    setRenamingId(null);
    if (!laneId || !name) return;
    const prev = data?.lanes.find((l) => l.id === laneId)?.name;
    updateLaneLocal(laneId, { name });
    try {
      // Optimistic like the pin: the name already changed in the list.
      await runAction(() => api.lanes.patch(laneId, { name }), {
        error: t('errors.rename'),
      });
    } catch {
      if (prev) updateLaneLocal(laneId, { name: prev });
    }
  }, [renamingId, renameText, data, updateLaneLocal, runAction]);

  if (loading) {
    return (
      <Working label={t('opening')} fill />
    );
  }

  // Router off — lanes have no engine (ADR-411 D2 gate). Honest state, no
  // dead affordances.
  if (!data?.enabled) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="max-w-sm text-center space-y-2 text-sm text-muted-foreground">
          <MessageCircle className="w-6 h-6 mx-auto text-muted-foreground/50" />
          <p className="font-medium text-foreground/80">{t('unavailableTitle')}</p>
          {/* §6.10b — this used to name the routing module by its internal
              name and report that it wasn't live: a module name shown to a
              member, asking them to care about an engine.

              2026-09-18 — and the replacement still said "on this deployment"
              (VOICE §3 bans it) and pointed at Freddie, a seat ADR-632 retired:
              an empty state sending a member to summon someone who no longer
              exists. The word map's own line for this state is "Chat isn't
              available here yet"; the second sentence names what puts something
              here (VOICE §1.6) instead of an absent colleague.

              The wording tracks the two inline versions of this same state
              (StudioSurface, TextEditor): "X isn't available here yet." plus
              what still works. VOICE §1.10 — one word per concept, product-wide.
              This pane has a TITLE slot those two lack, so the title carries
              the "isn't available" half and the body carries only the
              reassurance, rather than saying it twice. */}
          <p>{t('unavailableBody')}</p>
        </div>
      </div>
    );
  }

  // Worded here, never inline (the ADR-660 meter reads a JSX ternary as copy).
  const sideDoorLabel = side.shown ? t('supervision.hide') : t('supervision.show');

  // The new-chat flow is a MODAL (NewChatModal) — ADR-614 D1: it leads with
  // COLLEAGUES and keeps engines a click behind. People still join through the
  // CAST, from inside the conversation (ADR-495), which is why no human roster
  // is passed here.

  return (
    <div ref={setPaneNode} className="h-full flex min-h-0">
      {creating && (
        <NewChatModal
          agents={data?.agents ?? []}
          engines={data?.models ?? []}
          defaultEngine={data?.default_engine ?? null}
          onPick={async (choice) => {
            await createLane(choice);
          }}
          onClose={() => setCreating(false)}
        />
      )}
      {/* Lane list — flat recents, work-first (D4). At the narrowest rung it is
          the whole screen (w-full) and yields entirely once a lane is picked;
          above it, a column the member can hide and resize. A hidden rail is
          not rendered at all: hiding it with a class would leave its right
          border painting a seam down the edge of the conversation. */}
      <div
        style={railIsColumn ? { width: rail.width } : undefined}
        className={cn(
          'flex-col min-h-0',
          // The divider is a two-column artifact — full-width it's a hairline
          // against the screen edge.
          isNarrow ? 'w-full' : 'shrink-0 flex border-r border-border',
          isNarrow && (activeLane ? 'hidden' : 'flex'),
          !isNarrow && !rail.shown && 'hidden',
        )}
      >
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-border shrink-0">
          <span className="text-sm font-medium">{t('title')}</span>
          <div className="flex items-center gap-0.5">
            {/* Hide the rail. Only where it is a COLUMN — at the narrowest rung
                the rail IS the screen and hiding it would leave nothing. */}
            {railIsColumn && (
              <button
                onClick={rail.toggle}
                className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                aria-label={t('hideList')}
                title={t('hideList')}
                aria-expanded
              >
                <PanelLeft className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => setCreating((v) => !v)}
              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              aria-label={t('newChat')}
              title={t('newChat')}
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
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
              placeholder={t('search')}
              className="w-full rounded border border-input bg-background pl-7 pr-6 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5 rounded text-muted-foreground hover:text-foreground"
                aria-label={t('clearSearch')}
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* ADR-670 D4 — the index's two strips above the recents: what needs
            you (the one queue, D5), and who (the agents as faces — the
            who-filter made visible). Each is absent when it has nothing. */}
        <NeedsYouStrip onOpenLane={(laneId) => setParam({ lane: laneId, detail: null })} />
        <WhoStrip
          faces={whoFaces}
          selected={whoFilter}
          onChoose={chooseWho}
          onClear={() => setWhoFilter(null)}
        />

        <div className="flex-1 min-h-0 overflow-y-auto">
          {lanes.length === 0 && (
            <div className="px-4 py-8 text-center text-xs text-muted-foreground space-y-1.5">
              <p className="font-medium text-foreground/80">{t('noChatsTitle')}</p>
              {/* §6.10b — this used to open "a lane is a conversation pinned
                  to a MODEL OF YOUR CHOICE", which is the one question
                  ADR-460 D1 says a member must never be asked. The ADR-411
                  contract it carries (isolation · shared files · attribution)
                  is preserved — only the frame moves from engine to
                  colleague. */}
              <p>{t('noChatsBody')}</p>
            </div>
          )}
          {lanes.length === 0 && query.trim() && (
            <div className="px-4 py-6 text-center text-xs text-muted-foreground">
              {t('noMatches', { query: query.trim() })}
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
                    if (isSubmitKey(e, { allowShift: true })) void commitRename();
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
                kind={laneFaceKind(lane)}
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
                    aria-label={lane.pinned ? t('unpinLane') : t('pinLane')}
                    title={lane.pinned ? t('unpin') : t('pin')}
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
                    aria-label={t('renameChat')}
                    title={t('rename')}
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
                    aria-label={t('archive')}
                    title={t('archive')}
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

      {/* The rail's resize divider — a column edge, so only where the rail IS
          a column. */}
      {railIsColumn && (
        <div
          onPointerDown={rail.startResize}
          role="separator"
          aria-orientation="vertical"
          title={t('resizeRail')}
          className="w-1 shrink-0 cursor-col-resize bg-transparent transition-colors hover:bg-primary/20 active:bg-primary/30"
        />
      )}

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
        {activeLane && showDetail && !activeLane.skill ? (
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
            defaultResponder={defaultResponder}
            onBack={() => setParam({ detail: null })}
            onCastChanged={(participants) =>
              updateLaneLocal(activeLane.id, { participants })
            }
          />
        ) : activeLane ? (
          <>
          {/* ADR-670 D2 — canvas + side. The canvas (header + conversation)
              takes what the side leaves, so the conversation column (PANES
              §10) stays centred on the CANVAS, never on the pane. At
              single-pane the two are tabs of one screen; the panel stays
              MOUNTED behind the side tab so a streaming turn — and the files it
              is making — survive the switch. */}
          <div className="relative flex min-h-0 flex-1">
          <div
            className={cn(
              'min-w-0 flex-1 flex-col min-h-0',
              isNarrow && narrowPane === 'side' ? 'hidden' : 'flex',
            )}
          >
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
              // The way BACK. A hidden rail with no door is an inescapable
              // state (the ADR-519 lesson) — the member would have to reload.
              // Shown only when the rail is hidden and COULD be a column: at
              // the narrowest rung the crumb already returns to the list.
              leading={
                !isNarrow && !rail.shown ? (
                  <button
                    type="button"
                    onClick={rail.toggle}
                    className="shrink-0 -ml-1 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    title={t('showList')}
                    aria-label={t('showList')}
                    aria-expanded={false}
                  >
                    <PanelLeft className="h-4 w-4" />
                  </button>
                ) : null
              }
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
              // The side's DOOR, at every rung where the side is a column or
              // an overlay (PANES §3) — hidden only at single-pane, where the
              // bottom tab bar is the switcher.
              trailing={
                !isNarrow ? (
                  <button
                    type="button"
                    onClick={side.toggle}
                    className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    title={sideDoorLabel}
                    aria-label={sideDoorLabel}
                    aria-expanded={side.shown}
                  >
                    <PanelRight className="h-4 w-4" />
                  </button>
                ) : null
              }
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
              // Freshness follows every OTHER PRINCIPAL, not one species
              // (2026-08-14). The 2026-07-30 pass fixed a group-with-an-Agent
              // that polled never and left the mirror image standing: a solo-
              // human conversation with two Agents also polled never, so an
              // Agent turn addressed from another tab never arrived until
              // remount. The question is "can a turn arrive that I did not
              // cause?" — true whenever anyone else is in the cast.
              //
              // Reads the CAST, not `laneOthers` — that helper falls back to
              // the lane's own Agent for pre-cast (Studio/derive) lanes, so it
              // is never empty and would poll every solo lane forever.
              canReceiveOutOfBandTurns={
                (activeLane.participants ?? []).filter(
                  (p) => !(p.member_kind === 'human' && p.principal_id === userId),
                ).length > 0
              }
              viewerId={userId}
              principalLabels={Object.fromEntries(
                people.map((p) => [p.principal_id, p.label]),
              )}
              // The other half of the same lookup: a turn is authored by a
              // PRINCIPAL, and the transcript resolves humans and Agents the
              // same way (ADR-495 D3). Keyed by the whole roster rather than
              // this lane's cast, so a reply from an Agent since REMOVED from
              // the conversation still renders with its name and face — the
              // transcript is a historical record, not a live membership view.
              agentFaces={Object.fromEntries(
                (data?.agents ?? []).map((a) => [
                  a.slug,
                  { name: a.name, avatarUrl: a.avatar_url },
                ]),
              )}
              // The '@' roster: this conversation's cast, viewer excluded.
              // One species-blind gesture (ADR-605): an agent answers now; a
              // person gets the mention routed to their attention. The handle
              // is what the SERVER matches on — slug or display name,
              // space-squashed (the mention grammar is one token) — so the
              // menu can only ever emit something the parser honours.
              onDefaultResponderChange={setDefaultResponder}
              mentionCandidates={(activeLane.participants ?? [])
                .filter((p) => !(p.member_kind === 'human' && p.principal_id === userId))
                .map((p) => {
                  if (p.member_kind === 'agent') {
                    const a = agentBySlug(p.agent_slug);
                    return {
                      kind: 'agent' as const,
                      handle: a?.name?.replace(/\s+/g, '') || p.agent_slug || '',
                      name: a?.name || p.agent_slug || 'agent',
                      avatarUrl: a?.avatar_url,
                      blurb: a?.blurb,
                    };
                  }
                  const label =
                    people.find((x) => x.principal_id === p.principal_id)?.label ||
                    'A member';
                  return {
                    kind: 'human' as const,
                    handle: label.split('@')[0].replace(/\s+/g, ''),
                    name: label,
                  };
                })
                .filter((c) => c.handle)
                // G4 — workspace members NOT in this cast, as add-doors
                // (`inCast: false`): never mention targets, picking one
                // opens the add-participant drill-in below.
                .concat(
                  people
                    .filter(
                      (m) =>
                        !(activeLane.participants ?? []).some(
                          (p) => p.member_kind === 'human' && p.principal_id === m.principal_id,
                        ),
                    )
                    .map((m) => ({
                      kind: 'human' as const,
                      handle: m.label.split('@')[0].replace(/\s+/g, ''),
                      name: m.label,
                      inCast: false,
                    }))
                    .filter((c) => c.handle),
                )}
              onMentionOutsider={() => setParam({ detail: 'add' })}
              // G4 — the viewer's own handles, so a mention OF the reader
              // chips in their transcript (the roster above excludes them).
              extraKnownHandles={(wsMembers ?? [])
                .filter((m) => m.principal_id === userId)
                .flatMap((m) => {
                  const label = m.label ?? '';
                  return [
                    label.split('@')[0].replace(/\s+/g, ''),
                    label.replace(/\s+/g, ''),
                  ];
                })
                .filter(Boolean)}
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
              // ADR-670 D3 — what this conversation made, for the side.
              onArtifactsChange={setMadeHere}
            />
          </div>

          {/* The side: a COLUMN at the three-column rungs, an OVERLAY at
              two-pane (a scrim, Escape, and the door dismiss it), a full pane
              behind the bottom tab at single-pane. */}
          {wb.sideIsOverlay && side.shown && (
            <div
              role="presentation"
              onClick={side.toggle}
              className="absolute inset-0 z-20 bg-black/20"
            />
          )}
          {sideIsColumn && (
            <div
              onPointerDown={side.startResize}
              role="separator"
              aria-orientation="vertical"
              title={t('resizeRail')}
              className="w-1 shrink-0 cursor-col-resize bg-transparent transition-colors hover:bg-primary/20 active:bg-primary/30"
            />
          )}
          {(isNarrow ? narrowPane === 'side' : side.shown) && (
            <aside
              style={sideIsColumn ? { width: side.width } : undefined}
              aria-label={t('supervision.label')}
              className={cn(
                'flex min-h-0 flex-col overflow-y-auto bg-background',
                isNarrow
                  ? 'min-w-0 flex-1'
                  : wb.sideIsOverlay
                    ? 'absolute inset-y-0 right-0 z-30 w-[min(22rem,85%)] border-l border-border shadow-xl'
                    : 'shrink-0 border-l border-border',
              )}
            >
              <ChatSupervision laneId={activeLane.id} files={madeHere} />
            </aside>
          )}
          </div>

          {/* Single-pane: one screen, two tabs (PANES §2's last rung). The
              tuples hold CATALOG KEYS; the word is taken at render. */}
          {isNarrow && (
            <nav className="flex shrink-0 border-t border-border">
              {([
                ['conversation', 'supervision.tabConversation'],
                ['side', 'supervision.tabSide'],
              ] as const).map(([pane, labelKey]) => (
                <button
                  key={pane}
                  type="button"
                  aria-current={narrowPane === pane ? 'page' : undefined}
                  onClick={() => setNarrowPane(pane)}
                  className={cn(
                    'min-h-[44px] flex-1 py-2 text-xs font-medium transition-colors',
                    narrowPane === pane
                      ? 'border-t-2 border-foreground text-foreground'
                      : 'border-t-2 border-transparent text-muted-foreground',
                  )}
                >
                  {t(labelKey)}
                </button>
              ))}
            </nav>
          )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="max-w-sm text-center space-y-2 text-sm text-muted-foreground">
              <MessageCircle className="w-6 h-6 mx-auto text-muted-foreground/50" />
              <p className="font-medium text-foreground/80">{t('emptyTitle')}</p>
              {/* §6.10b — same re-frame as the two empty states above: a
                  chat is with a COLLEAGUE, not with a chosen engine.

                  "on the left" is only true while the rail IS on the left. With
                  it hidden the sentence pointed at nothing and the surface had
                  no visible way back — an empty state that names an absent
                  affordance reads as a broken product, not a hidden one. */}
              {/* ADR-660 — one WHOLE message per branch. The English version
                  concatenated three fragments with a leading space, which is a
                  word order, not a sentence. */}
              <p>{railIsColumn ? t('emptyBodyWithRail') : t('emptyBodyNoRail')}</p>
              {!isNarrow && !rail.shown && (
                <button
                  type="button"
                  onClick={rail.toggle}
                  className="mx-auto mt-1 inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs text-foreground/80 transition-colors hover:bg-muted"
                >
                  <PanelLeft className="h-3.5 w-3.5" />
                  {t('showListAction')}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
