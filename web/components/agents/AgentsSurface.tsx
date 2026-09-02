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
import { useSearchParams } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';
import { AgentIcon } from './AgentIcon';

// Provenance, rendered from the field. A member-authored agent simply lacks
// the mark — there is no "yours" badge, because the member already knows.
function KernelMark() {
  return (
    <span
      className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
      title="Comes with yarnnn — you can't edit this one."
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
      {Icon ? <Icon className="h-3.5 w-3.5 text-muted-foreground" /> : null}
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
  offered: boolean;
  kernel: boolean;
  /** The apps this agent works in, as the APP's own identity — title +
   *  `icon_key` + route, served from the surface rows (ADR-631: one relation).
   *  Rendered as chips carrying the SAME mark the Dock shows. */
  apps: { slug: string; title: string; icon_key: string; route: string }[];
  /** The engine behind the name (ADR-460 D4). Served so the page can say what
   *  actually runs this agent rather than implying it. */
  model?: string;
  /** ADR-624 D4 — WHERE what this agent knows lives. An ADDRESS, never the
   *  contents: memory is ordinary substrate, so the page opens the Files door
   *  rather than hosting a second reading face (ADR-595 D1, one surface out). */
  memory_path?: string;
};

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
        No connections yet — connect one in Settings, then scope it here.
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
          Following your connections — including any you add later.
        </p>
      ) : (optIn ?? []).length === 0 ? (
        <p className="text-[11px] text-muted-foreground">
          Reads through no connection.
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
  onScope,
  onBack,
}: {
  agent: AgentRow;
  available: string[];
  optIn: Record<string, string[]>;
  onScope: (slug: string, platforms: string[] | null) => Promise<void>;
  onBack: () => void;
}) {
  // The Files door for the Memory row — the SAME `navigateToSurface('files',
  // { path })` the Strings pane opens its subject with, so a agent's memory
  // lands in the one place files are read.
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
        All agents
      </button>

      <header className="flex items-start gap-3">
        <div className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-full bg-muted">
          <AgentIcon icon={agent.icon} />
        </div>
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
          <dt className="w-24 shrink-0 text-muted-foreground">Works in</dt>
          <dd>
            {agent.apps.length ? (
              <AppChips agent={agent} />
            ) : (
              'Anywhere you invite them'
            )}
          </dd>
        </div>
        <div className="flex gap-3">
          <dt className="w-24 shrink-0 text-muted-foreground">Add to a chat</dt>
          <dd>Yes — start a chat with them, or add them to one you are in.</dd>
        </div>
        {agent.model && (
          <div className="flex gap-3">
            <dt className="w-24 shrink-0 text-muted-foreground">Runs on</dt>
            <dd className="break-all">{agent.model}</dd>
          </div>
        )}
        {/* ADR-624 D4 — what this agent has learned. The row is an ADDRESS and
            a DOOR, never a viewer: memory is ordinary substrate, so it opens in
            Files like any other folder. A private renderer here would be the
            second reading face ADR-595 D1 deleted a canvas to avoid. */}
        {agent.memory_path && (
          <div className="flex gap-3">
            <dt className="w-24 shrink-0 text-muted-foreground">Memory</dt>
            <dd className="min-w-0 flex-1">
              <button
                type="button"
                onClick={() => navigateToSurface('files', { path: memoryPath })}
                className="text-left underline underline-offset-2 hover:text-foreground"
              >
                What {agent.name} has learned
              </button>
              <p className="mt-1 text-[11px] text-muted-foreground leading-relaxed">
                Kept as ordinary files in the workspace — attributed, versioned,
                and yours to read or correct.
              </p>
            </dd>
          </div>
        )}
        <div className="flex gap-3">
          <dt className="w-24 shrink-0 text-muted-foreground">Connections</dt>
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
  const params = useSearchParams();
  const { setSurfaceParams } = useSurfacePreferences();
  const [agents, setAgents] = useState<AgentRow[] | null>(null);
  // ADR-612 — the member's connector scoping. `available` is what there is to
  // opt into (the grant side); `optIn` is per agent. An agent ABSENT from the
  // map is not scoped and reaches everything granted — absence must never be
  // read as "nothing", which is the whole default this feature rests on.
  const [available, setAvailable] = useState<string[]>([]);
  const [optIn, setOptIn] = useState<Record<string, string[]>>({});
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
    const res = await api.agentConnectors.set(slug, platforms);
    setOptIn(res.opt_in ?? {});
  };

  useEffect(() => {
    let alive = true;
    api.lanes
      .list(true)
      .then((res) => {
        if (!alive) return;
        setAgents((res.agents ?? []) as AgentRow[]);
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
          onScope={scopeConnectors}
          onBack={() => open(null)}
        />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-2xl space-y-8">
        <header className="space-y-1">
          <h1 className="text-sm font-medium">Agents</h1>
          {/* The second sentence described a roster that does not exist yet
              (nobody is `offered`, ADR-599 D1) — the same unfulfillable
              promise as the empty section below it. Says what IS true. */}
          <p className="text-xs text-muted-foreground leading-relaxed">
            Who works with you here. Each one lives in an app — you meet them
            where the work is.
          </p>
        </header>

        <section className="space-y-3">
          <h2 className="text-xs font-medium text-muted-foreground">
            In an app
          </h2>
          {housed.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              {agents === null
                ? 'Could not load this.'
                : 'None yet.'}
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
                  <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-muted">
                    <AgentIcon icon={b.icon} />
                  </div>
                  <div className="min-w-0 space-y-1.5">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <span className="text-sm font-medium">{b.name}</span>
                      {b.kernel && <KernelMark />}
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {b.blurb}
                    </p>
                    <AppChips agent={b} />
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
            To work with
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
                  <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-muted">
                    <AgentIcon icon={b.icon} />
                  </div>
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
