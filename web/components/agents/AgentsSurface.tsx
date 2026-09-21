'use client';

/**
 * AgentsSurface — the agents that exist, sectioned by where they live
 * (ADR-600 D6, 2026-08-24).
 *
 * The predecessor rendered a single empty state: "No agents to hire yet". That
 * was true about the ROSTER and false about the member's day — Designer had
 * answered them in Slides an hour earlier. ADR-600 collapsed the register
 * split, so "is this agent hireable?" is a field (`offered`), and the honest
 * surface shows every agent with the app it speaks for:
 *
 *   - AT A PANE   — `offered: false`. Met in its app, never invited.
 *   - TO WORK WITH — `offered: true`. Empty today (ADR-599 D1 left nobody
 *     offered); that section carries the empty state, which is the one the
 *     operator actually ruled on.
 *
 * ADR-602 D6 — LIST/DETAIL. `?agents.agent={slug}` opens one agent's page:
 * who they are, where they work, what runs them, and whether you can change
 * them. The param is already sanctioned (`SURFACE_PARAM_KEYS.agents`) and
 * already EPHEMERAL (`SURFACE_EPHEMERAL_PARAM_KEYS`) — a roster's point is
 * the list, so a launch must never land on one member's page. Depth changes
 * via `setSurfaceParams`, never a pathname flip (the shell effects branch on
 * the `/desktop` baseline).
 *
 * A kernel agent's page is READ-ONLY, and says so plainly. Editability is
 * `assert_editable`'s to enforce server-side (ADR-601 D3) — this surface
 * states it, and must never be the only thing that does.
 *
 * ADR-601 D4 — two facts are rendered from FIELDS the server sends, never
 * inferred: `kernel` (yarnnn authored this agent, so its character is not
 * editable — shown so the distinction is legible before the first
 * member-authored agent exists) and `apps` (a LIST — one agent may serve
 * several apps since ADR-601 D1, so "Editor — Text, Blogger" reads directly
 * instead of one-to-one agent inferred from silence).
 *
 * Server-driven, deliberately: the roster comes from `lanes.list().agents`,
 * which the API builds from the SAME registry the prompt uses. The previous
 * version hardcoded "Designer in Slides, Editor in Text, Keeper in Strings"
 * (a roster that has since moved twice — ADR-602, ADR-610 — which is the point)
 * in prose — a fourth agent would silently never have appeared (the ADR-562
 * second-home failure, in copy rather than in code).
 */

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { ArrowLeft, ChevronDown } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { resolveSurfaceIcon, resolveSurfaceAccent } from '@/lib/shell/surface-icons';
import { AgentMark } from './AgentIcon';
import { EngineChooserModal, type EngineRow } from './EngineChooserModal';
import { cn } from '@/lib/utils';
import { useFeedback } from '@/contexts/FeedbackContext';

// Provenance, rendered from the field. A member-authored agent simply lacks
// the mark — there is no "yours" badge, because the member already knows.
function KernelMark() {
  const t = useTranslations('text.agents');
  return (
    <span
      className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
      title={t('kernelMark')}
    >
      yarnnn
    </span>
  );
}

// An app, shown as the member already knows it: the Dock's own mark and name.
// The icon resolves through `resolveSurfaceIcon` — the SAME resolver the Dock
// and Launcher use (ADR-297) — so an app has one look everywhere and a re-icon
// moves every rendering at once. An app that predates the `apps` payload has
// no icon_key; the chip still renders, named, rather than disappearing.
function AppChip({ app }: { app: { slug: string; title: string; icon_key: string } }) {
  const Icon = app.icon_key ? resolveSurfaceIcon(app.icon_key) : null;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-border/60 bg-muted/40 px-2 py-1 text-[11px] font-medium text-foreground/80">
      {/* ADR-641 — the chip carries the APP's own accent, the same hue that
          app wears in the Dock and Launcher. On a row whose glyph says
          "agent" (violet), the chips are what say WHICH apps. */}
      {Icon ? <Icon className={cn('h-3.5 w-3.5', resolveSurfaceAccent(app.slug))} /> : null}
      {app.title}
    </span>
  );
}

// The apps an agent works in, as chips carrying the Dock's own mark (ADR-631:
// one served relation, `apps`).
function AppChips({ agent }: { agent: AgentRow }) {
  if (!agent.apps?.length) return null;
  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {agent.apps.map((a) => (
        <AppChip key={a.slug} app={a} />
      ))}
    </span>
  );
}

type AgentRow = {
  slug: string;
  name: string;
  blurb: string;
  icon: string;
  /** ADR-641 amendment — the agent's face, when one exists (a mirrored kernel
   *  face, or the member's own upload, which wins). Absent is ordinary: the
   *  mark falls back to the craft glyph. */
  avatar_url?: string | null;
  offered: boolean;
  kernel: boolean;
  /** The apps this agent works in, as the APP's own identity — title +
   *  `icon_key` + route, served from the surface rows (ADR-631: one relation).
   *  Rendered as chips carrying the SAME mark the Dock shows. */
  apps: { slug: string; title: string; icon_key: string; route: string }[];
  /** The engine behind the name (ADR-460 D4). Served so the page can say what
   *  actually runs this agent rather than implying it. ADR-654: this is what
   *  runs it NOW — the member's override when set, else the declared engine. */
  model?: string;
  /** ADR-654 D4 — the kernel's declared engine, so the door can offer "back to
   *  the default" and NAME it rather than describing it. */
  model_default?: string;
  /** ADR-654 D4 — what THIS member chose for this agent, absent when they have
   *  not chosen. A FIELD, not an inference from `model !== model_default`:
   *  choosing the default explicitly is a real choice and must render as one. */
  model_override?: string | null;
  /** ADR-624 D4 — WHERE what this agent knows lives. An ADDRESS, never the
   *  contents: memory is ordinary substrate, so the page opens the Files door
   *  rather than hosting a second reading face (ADR-595 D1, one surface out). */
  memory_path?: string;
  /** ADR-640 D2 — the CRAFT this agent can be met with: the kernel skills
   *  whose apps meet its apps. Derived server-side from the same rule the
   *  frame runs; read-only, never assigned. */
  craft?: { slug: string; title: string; path: string }[];
  /** ADR-640 D2 — the files this agent keeps current: the standing
   *  declarations whose executor resolves to it. Derived from the same
   *  discovery the drain runs; read-only. Not a history (D1). */
  tending?: { topic: string; target_path?: string | null }[];
};


/** One agent's engine, as a quiet tag on the roster row (ADR-654 D4).
 *
 * Reads the same `models` roster the picker does, so the list and the detail
 * page can never name an engine differently. Falls back to the raw id ONLY if
 * the roster has not loaded — a member should never read a routing key, but a
 * blank where the engine should be is worse than an ugly one.
 *
 * An override is not marked here. The roster answers "what runs this agent",
 * and whether that came from a default or a choice is the detail page's
 * question — a badge for it would put emphasis on a row that is chrome.
 */
function EngineTag({ agent, models }: { agent: AgentRow; models: EngineRow[] }) {
  if (!agent.model) return null;
  const label = models.find((m) => m.id === agent.model)?.label ?? agent.model;
  return (
    <span className="text-[11px] text-muted-foreground/80">{label}</span>
  );
}

/** The engine a member has chosen for one agent (ADR-654 D4).
 *
 * The door ADR-647 shipped without: `default_engine` has been read by
 * ChatSurface and written by NOTHING since 2026-09-08, so a member could not
 * set the preference the lane already consulted.
 *
 * ⭐ THE LABEL, NOT THE ROUTING KEY. This pane rendered `anthropic/claude-sonnet-5`
 * verbatim. `LANE_MODELS` carries `label` for exactly this, and the registry is
 * emphatic that a label is not chrome — it is written into every revision's
 * attribution and is what the model is TOLD IT IS. A member reads "Claude
 * Sonnet 5"; the routing key stays server-side where it belongs.
 */
function EnginePicker({
  agent,
  models,
  onChange,
}: {
  agent: AgentRow;
  models: EngineRow[];
  onChange: (model: string | null) => Promise<void>;
}) {
  const t = useTranslations('text.agents');
  const [open, setOpen] = useState(false);
  const current = agent.model ?? '';
  const declared = agent.model_default ?? '';
  const labelFor = (id: string) => models.find((m) => m.id === id)?.label ?? id;
  const chosen = models.find((m) => m.id === current);

  return (
    <div className="min-w-0 flex-1 space-y-1.5">
      {/* A BUTTON, not a <select> (operator, 2026-09-17). A native select
          commits on `change`, which a stray scroll or arrow key fires — so
          re-pointing an agent could happen by accident, with no confirm step
          and no undo. The act is deliberate now: this opens the chooser, and
          nothing is written until the member confirms there. */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs text-foreground transition-colors hover:bg-muted/60"
      >
        {current ? labelFor(current) : t('chooseEngine')}
        {agent.model_override && (
          <span className="text-[10px] text-muted-foreground">{t('yours')}</span>
        )}
        <ChevronDown className="h-3 w-3 text-muted-foreground" aria-hidden />
      </button>
      {/* An engine the member CHOSE that cannot run right now says so here.
          The creation door narrows past it to the default (ADR-654 D2), so the
          honest sentence is "not running", never a silent substitution. */}
      {chosen?.available === false && (
        <p className="text-[11px] text-amber-600 dark:text-amber-500">
          {/* ONE sentence per arm, never a join: a detail glued on with an
              em dash in code is an English word order (ADR-660). */}
          {chosen.unavailable_detail
            ? t('engineUnavailableDetail', {
                label: chosen.label,
                detail: chosen.unavailable_detail,
              })
            : t('engineUnavailable', { label: chosen.label })}{' '}
          {t('engineFallback', {
            engine: declared ? labelFor(declared) : t('engineDefault'),
          })}
        </p>
      )}
      <p className="text-[11px] text-muted-foreground">
        {t('engineApplies')}
      </p>
      <EngineChooserModal
        open={open}
        onClose={() => setOpen(false)}
        agentName={agent.name}
        models={models}
        current={current}
        declared={declared}
        override={agent.model_override}
        onConfirm={onChange}
      />
    </div>
  );
}

// The connector scoping control (ADR-612, defaults settled by ADR-615). Three
// states a member can express, and they must stay distinguishable:
//   not scoped (absent)  — reaches every connected platform. The DEFAULT.
// ADR-615: that default now holds at EVERY surface the member works in — a
// pane turn is the same principal as a chat turn, so these toggles are purely
// SUBTRACTIVE. What they narrow is the member's own grant, never a agent's
// authority (the ADR-596 D1 cliff test).
//   a subset             — reaches only those.
//   scoped to none ([])  — reaches nothing, deliberately.
// "Not scoped" is NOT the same as "all boxes ticked": ticking every box is a
// standing choice that silently stops tracking a platform connected later,
// while absence follows the grant. The row therefore offers an explicit
// "Everything connected" reset rather than inferring it from a full set.
function ConnectorScope({
  slug,
  available,
  optIn,
  onChange,
}: {
  slug: string;
  available: string[];
  optIn: string[] | undefined;
  onChange: (platforms: string[] | null) => void;
}) {
  const t = useTranslations('text.agents');
  const scoped = optIn !== undefined;
  const [busy, setBusy] = useState(false);

  const save = async (next: string[] | null) => {
    setBusy(true);
    try {
      await onChange(next);
    } finally {
      setBusy(false);
    }
  };

  if (available.length === 0) {
    return (
      <span className="text-muted-foreground">
        {t('noConnections')}
      </span>
    );
  }

  return (
    <div className="space-y-2">
      <div className="space-y-1">
        {available.map((p) => {
          const on = !scoped || (optIn ?? []).includes(p);
          return (
            <button
              key={p}
              type="button"
              role="switch"
              aria-checked={on}
              aria-label={p}
              disabled={busy}
              onClick={() => {
                const base = scoped ? optIn ?? [] : available;
                const next = base.includes(p)
                  ? base.filter((x) => x !== p)
                  : [...base, p];
                void save(next);
              }}
              className="flex w-full items-center justify-between gap-3 rounded-md px-1.5 py-1 text-left transition-colors hover:bg-muted/50 disabled:opacity-60"
            >
              <span
                className={
                  'text-xs capitalize ' +
                  (on ? 'text-foreground' : 'text-muted-foreground')
                }
              >
                {p}
              </span>
              {/* A switch, not a struck-through label: "off" is a STATE the
                  member can flip, and strikethrough reads as deleted rather
                  than available-but-unselected. `role="switch"` carries the
                  state to assistive tech, which the plain button did not. */}
              <span
                aria-hidden="true"
                className={
                  'relative h-4 w-7 shrink-0 rounded-full transition-colors ' +
                  (on ? 'bg-foreground/80' : 'bg-border')
                }
              >
                <span
                  className={
                    'absolute top-0.5 h-3 w-3 rounded-full bg-background transition-all ' +
                    (on ? 'left-3.5' : 'left-0.5')
                  }
                />
              </span>
            </button>
          );
        })}
      </div>
      {/* Only what the switches CANNOT say themselves. Listing the selected
          platforms back ("Only notion, slack") restated the toggle row
          verbatim. Two states remain worth a line because they are invisible
          in the switches alone:
            - UNSCOPED reads identical to "all switched on", but behaves
              differently — it follows connections added later.
            - SCOPED TO NOTHING is all-off, which could be misread as an
              unsaved state rather than a deliberate choice.

          ⚠️ THE RESET LINK IS DELETED (operator ruling, 2026-08-27), and with
          it the only caller of `save(null)`. UNSCOPED is therefore no longer
          REACHABLE from this surface once a member scopes an agent: the toggles
          always send an array, so every later state is an explicit list.
          `null` remains meaningful in the API and the store — ADR-612 D2's
          absent≠empty is unchanged, and it is still what every agent starts
          as — but the member cannot return to it here. Accepted knowingly as
          the price of a surface that states only what it must. */}
      {!scoped ? (
        <p className="text-[11px] text-muted-foreground">
          {t('followingConnections')}
        </p>
      ) : (optIn ?? []).length === 0 ? (
        <p className="text-[11px] text-muted-foreground">
          {t('noConnection')}
        </p>
      ) : null}
    </div>
  );
}

/** One agent's page. Read-only for a kernel agent — stated, not merely
 *  unbuilt (ADR-601 D3's chokepoint is the enforcement; this is the telling). */
function AgentDetail({
  agent,
  available,
  optIn,
  models,
  onScope,
  onSetEngine,
  onBack,
}: {
  agent: AgentRow;
  available: string[];
  optIn: Record<string, string[]>;
  models: EngineRow[];
  onScope: (slug: string, platforms: string[] | null) => Promise<void>;
  onSetEngine: (slug: string, model: string | null) => Promise<void>;
  onBack: () => void;
}) {
  // The Files door for the Memory row — the SAME `navigateToSurface('files',
  // { path })` the Strings pane opens its subject with, so a agent's memory
  // lands in the one place files are read.
  const t = useTranslations('text.agents');
  const { navigateToSurface } = useSurfacePreferences();
  // Bound outside the closure so the narrowing survives into the handler.
  const memoryPath = agent.memory_path ?? '';
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        {t('allAgents')}
      </button>

      <header className="flex items-start gap-3">
        <AgentMark
          icon={agent.icon}
          avatarUrl={agent.avatar_url}
          name={agent.name}
          className="mt-0.5"
        />
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <h1 className="text-sm font-medium">{agent.name}</h1>
            {agent.kernel && <KernelMark />}
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {agent.blurb}
          </p>
        </div>
      </header>

      <dl className="space-y-3 text-xs">
        <div className="flex gap-3">
          <dt className="w-24 shrink-0 text-muted-foreground">{t('worksIn')}</dt>
          <dd>
            {agent.apps.length ? (
              <AppChips agent={agent} />
            ) : (
              t('worksInAnywhere')
            )}
          </dd>
        </div>
        <div className="flex gap-3">
          <dt className="w-24 shrink-0 text-muted-foreground">{t('addToChat')}</dt>
          <dd>{t('addToChatBody')}</dd>
        </div>
        {/* ADR-654 D4 — the engine is the member's CHOICE, not a statement
            about them. Every offered engine, every provider; an unavailable one
            greyed WITH its reason rather than filtered (ADR-559 D3). */}
        {(agent.model || models.length > 0) && (
          <div className="flex gap-3">
            <dt className="w-24 shrink-0 text-muted-foreground">{t('runsOn')}</dt>
            <dd className="min-w-0 flex-1">
              <EnginePicker
                agent={agent}
                models={models}
                onChange={(model) => onSetEngine(agent.slug, model)}
              />
            </dd>
          </div>
        )}
        {/* ADR-640 D2 — two relations the kernel DERIVES, stated read-only.
            Neither is a record of what the agent has done: craft is which
            skills meet its apps, tending is which files resolve to it. Each
            entry is a DOOR into Files, never a viewer here (ADR-595 D1). */}
        {agent.craft && agent.craft.length > 0 && (
          <div className="flex gap-3">
            <dt className="w-24 shrink-0 text-muted-foreground">{t('skills')}</dt>
            <dd className="min-w-0 flex-1">
              <ul className="flex flex-wrap gap-x-3 gap-y-1">
                {agent.craft.map((c) => (
                  <li key={c.slug}>
                    <button
                      type="button"
                      onClick={() => navigateToSurface('files', { path: `/workspace/${c.path}` })}
                      className="text-left underline underline-offset-2 hover:text-foreground"
                    >
                      {c.title}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="mt-1 text-[11px] text-muted-foreground leading-relaxed">
                {t('skillsBody', { name: agent.name })}
              </p>
            </dd>
          </div>
        )}
        {agent.tending && agent.tending.length > 0 && (
          <div className="flex gap-3">
            <dt className="w-24 shrink-0 text-muted-foreground">{t('keepsCurrent')}</dt>
            <dd className="min-w-0 flex-1">
              <ul className="space-y-0.5">
                {agent.tending.map((t) => (
                  <li key={t.topic}>
                    <button
                      type="button"
                      onClick={() => navigateToSurface('files', { path: t.target_path ?? `/workspace/${t.topic}` })}
                      className="text-left underline underline-offset-2 hover:text-foreground break-all"
                    >
                      {t.target_path ? t.target_path.replace(/^\/workspace\//, '') : t.topic}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="mt-1 text-[11px] text-muted-foreground leading-relaxed">
                {t('keepsCurrentBody', { name: agent.name })}
              </p>
            </dd>
          </div>
        )}
        {/* ADR-624 D4 — what this agent has learned. The row is an ADDRESS and
            a DOOR, never a viewer: memory is ordinary substrate, so it opens in
            Files like any other folder. A private renderer here would be the
            second reading face ADR-595 D1 deleted a canvas to avoid. */}
        {agent.memory_path && (
          <div className="flex gap-3">
            <dt className="w-24 shrink-0 text-muted-foreground">{t('memory')}</dt>
            <dd className="min-w-0 flex-1">
              <button
                type="button"
                onClick={() => navigateToSurface('files', { path: memoryPath })}
                className="text-left underline underline-offset-2 hover:text-foreground"
              >
                {t('memoryLink', { name: agent.name })}
              </button>
              <p className="mt-1 text-[11px] text-muted-foreground leading-relaxed">
                {t('memoryBody')}
              </p>
            </dd>
          </div>
        )}
        <div className="flex gap-3">
          <dt className="w-24 shrink-0 text-muted-foreground">{t('connections')}</dt>
          <dd className="min-w-0 flex-1">
            <ConnectorScope
              slug={agent.slug}
              available={available}
              optIn={optIn[agent.slug]}
              onChange={(platforms) => onScope(agent.slug, platforms)}
            />
          </dd>
        </div>
        {/* The "Editing" row is DELETED (operator ruling, 2026-08-27): the
            `yarnnn` badge beside the name already states provenance, and the
            controls being live or absent already shows what may be changed.
            A row that restates two things the surface shows is the same
            tautology the scope summary was cut for. `assert_editable`
            (ADR-601 D3) remains the enforcement — this was only the telling. */}
      </dl>

    </div>
  );
}

export function AgentsSurface() {
  const t = useTranslations('text.agents');
  const surfaces = useTranslations('surfaces');
  const { runAction } = useFeedback();
  const params = useSearchParams();
  const { setSurfaceParams } = useSurfacePreferences();
  const [agents, setAgents] = useState<AgentRow[] | null>(null);
  // ADR-612 — the member's connector scoping. `available` is what there is to
  // opt into (the grant side); `optIn` is per agent. An agent ABSENT from the
  // map is not scoped and reaches everything granted — absence must never be
  // read as "nothing", which is the whole default this feature rests on.
  const [available, setAvailable] = useState<string[]>([]);
  const [optIn, setOptIn] = useState<Record<string, string[]>>({});
  // ADR-654 D4 — the engine roster, from the SAME envelope as the agents. No
  // second endpoint and no FE table: `models` is what the chat chooser already
  // reads, so the two doors cannot offer different engines.
  const [models, setModels] = useState<EngineRow[]>([]);
  // Read UNPREFIXED: the shell owns the `agents.` namespacing on the way in
  // and out (surface-preferences), and a surface reads its own key plainly —
  // the SettingsPaneShell `tab` precedent.
  const selectedSlug = params.get('agent') || '';
  const selected = (agents ?? []).find((b) => b.slug === selectedSlug) ?? null;

  // The crumb follows the depth, so the address bar and the trail agree.
  useWindowCrumb('agents', selected ? [{ label: selected.name }] : []);

  // `setSurfaceParams`, never a pathname flip: the shell's foreground effects
  // branch on the `/desktop` baseline, and a flip here trips all three
  // (surface-preferences §depth). null clears the key — back to the list.
  const open = (slug: string | null) => setSurfaceParams({ agent: slug });

  // ADR-612 — save the scoping, then hold the SERVER's map rather than a
  // locally-patched one: the server is what the turn will actually read, and
  // a client that kept its own optimistic copy would show a scoping the lane
  // does not have.
  const scopeConnectors = async (slug: string, platforms: string[] | null) => {
    // Neither of these two verbs had a try/catch at all: a rejection was an
    // unhandled promise, so a failed scoping left the switch showing a
    // reach the agent does not have and said nothing.
    const res = await runAction(() => api.agentConnectors.set(slug, platforms), {
      pending: t('savingPending'),
      success: t('scopeSaved'),
      error: t('scopeError'),
    });
    setOptIn(res.opt_in ?? {});
  };

  // ADR-654 D4 — the member's engine choice for ONE agent, through the generic
  // member-state door (no bespoke endpoint for one key).
  //
  // Patched locally rather than re-fetched: unlike connector scoping, which
  // holds the SERVER's map because the server resolves the whole relation, this
  // is one value the member just set and the server stores verbatim. Clearing
  // returns the row to its declared engine, which is `model_default` — the same
  // value the server would send back.
  const setAgentEngine = async (slug: string, model: string | null) => {
    // ⭐ `{}`, NOT `null`, to clear. The member-state door declares
    // `value: Any = Body(...)` — REQUIRED — and FastAPI reads a bare JSON
    // `null` body as a MISSING body, so clearing 422'd with "Field required"
    // while setting worked fine. Found by driving the reset on prod; no
    // structural check could see it, because both arms are one call.
    //
    // An empty object is a stored value the resolver already handles: it has
    // no `model` key, so `_read_member_state_engine` returns None and the next
    // step of the precedence stands — the same outcome as no row at all. The
    // narrowing is what makes this safe, so the clear needs no new path.
    await runAction(
      () => api.memberState.put(`agent_engine:${slug}`, model ? { model } : {}),
      {
        pending: t('savingPending'),
        success: model ? t('engineChanged') : t('engineCleared'),
        error: t('engineError'),
      },
    );
    setAgents((prev) =>
      (prev ?? []).map((a) =>
        a.slug === slug
          ? { ...a, model_override: model, model: model || a.model_default || '' }
          : a,
      ),
    );
  };

  useEffect(() => {
    let alive = true;
    api.lanes
      .list(true)
      .then((res) => {
        if (!alive) return;
        setAgents((res.agents ?? []) as AgentRow[]);
        setModels((res.models ?? []) as EngineRow[]);
      })
      // A failed read must not render as "you have nobody" — that is the exact
      // false statement this surface exists to stop telling.
      .catch(() => alive && setAgents(null));
    api.agentConnectors
      .get()
      .then((res) => {
        if (!alive) return;
        setAvailable(res.available ?? []);
        setOptIn(res.opt_in ?? {});
      })
      // A failed read leaves the map empty = "nothing scoped", which renders
      // as today's behaviour rather than as a false restriction.
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const housed = (agents ?? []).filter((b) => !b.offered);
  const offered = (agents ?? []).filter((b) => b.offered);

  if (selected) {
    return (
      <div className="h-full overflow-y-auto px-6 py-8">
        <AgentDetail
          agent={selected}
          available={available}
          optIn={optIn}
          models={models}
          onScope={scopeConnectors}
          onSetEngine={setAgentEngine}
          onBack={() => open(null)}
        />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-2xl space-y-8">
        <header className="space-y-1">
          <h1 className="text-sm font-medium">{surfaces('agents.title')}</h1>
          {/* The second sentence described a roster that does not exist yet
              (nobody is `offered`, ADR-599 D1) — the same unfulfillable
              promise as the empty section below it. Says what IS true.
              ADR-654: "each one lives in an app" also said what every row's
              app chip ALREADY shows, a third telling after the chip and the
              old section header. What a member cannot see from the rows is
              that the engine is theirs to change. */}
          <p className="text-xs text-muted-foreground leading-relaxed">
            {t('lede')}
          </p>
        </header>

        {/* NO section header here. "In an app" was a discriminator label with
            nothing to discriminate against: its only sibling ("To work with")
            renders when `offered.length > 0`, and nobody is offered (ADR-599
            D1), so the page showed ONE group under a heading naming what every
            row's own app chip already said. A discriminator and a constant must
            not share a shape (ADR-629 D4 lesson). The header returns with its
            sibling, in one edit, the moment an agent is offered. */}
        <section className="space-y-3">
          {housed.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              {agents === null
                ? t('loadFailed')
                : t('noneYet')}
            </p>
          ) : (
            <ul className="space-y-2">
              {housed.map((b) => (
                <li key={b.slug}>
                  <button
                    type="button"
                    onClick={() => open(b.slug)}
                    className="flex w-full items-start gap-3 rounded-lg border border-border/60 p-3 text-left transition-colors hover:bg-muted/50"
                  >
                  <AgentMark
                    icon={b.icon}
                    avatarUrl={b.avatar_url}
                    name={b.name}
                    size="sm"
                    className="mt-0.5"
                  />
                  <div className="min-w-0 space-y-1.5">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <span className="text-sm font-medium">{b.name}</span>
                      {b.kernel && <KernelMark />}
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {b.blurb}
                    </p>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
                      <AppChips agent={b} />
                      {/* ADR-654 D4 — the engine, on the ROSTER and not only on
                          the detail page. A member comparing who works for them
                          is comparing engines too, and "which of these is on
                          Opus" was a three-click question. The LABEL, never the
                          routing key. */}
                      <EngineTag agent={b} models={models} />
                    </div>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* "To work with" — the OFFERED agents. Rendered only when there ARE
            any: nobody is offered today (ADR-599 D1) and member-authored
            agents are ruled out for MVP 1.0, so the section could only ever
            show an empty box promising a feature that is not coming yet. A
            standing promise a member cannot act on is worse than silence.
            The `offered` FIELD is untouched — it still gates the cast door —
            and the moment an agent carries it, this section appears with no
            edit here. Deleting the branch, not the capability. */}
        {offered.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xs font-medium text-muted-foreground">
            {t('toWorkWith')}
          </h2>
          {(
            <ul className="space-y-2">
              {offered.map((b) => (
                <li key={b.slug}>
                  <button
                    type="button"
                    onClick={() => open(b.slug)}
                    className="flex w-full items-start gap-3 rounded-lg border border-border/60 p-3 text-left transition-colors hover:bg-muted/50"
                  >
                  <AgentMark
                    icon={b.icon}
                    avatarUrl={b.avatar_url}
                    name={b.name}
                    size="sm"
                    className="mt-0.5"
                  />
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <span className="text-sm font-medium">{b.name}</span>
                      {b.kernel && <KernelMark />}
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {b.blurb}
                    </p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        )}
      </div>
    </div>
  );
}
