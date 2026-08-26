'use client';

/**
 * AgentsSurface — the beings that exist, sectioned by where they live
 * (ADR-600 D6, 2026-08-24).
 *
 * The predecessor rendered a single empty state: "No agents to hire yet". That
 * was true about the ROSTER and false about the member's day — Designer had
 * answered them in Slides an hour earlier. ADR-600 collapsed the register
 * split, so "is this being hireable?" is a field (`offered`), and the honest
 * surface shows every being with the desk it speaks for:
 *
 *   - AT A DESK   — `offered: false`. Met in its app, never invited.
 *   - TO WORK WITH — `offered: true`. Empty today (ADR-599 D1 left nobody
 *     offered); that section carries the empty state, which is the one the
 *     operator actually ruled on.
 *
 * ADR-602 D6 — LIST/DETAIL. `?agents.agent={slug}` opens one being's page:
 * who they are, where they work, what runs them, and whether you can change
 * them. The param is already sanctioned (`SURFACE_PARAM_KEYS.agents`) and
 * already EPHEMERAL (`SURFACE_EPHEMERAL_PARAM_KEYS`) — a roster's point is
 * the list, so a launch must never land on one member's page. Depth changes
 * via `setSurfaceParams`, never a pathname flip (the shell effects branch on
 * the `/desktop` baseline).
 *
 * A kernel being's page is READ-ONLY, and says so plainly. Editability is
 * `assert_editable`'s to enforce server-side (ADR-601 D3) — this surface
 * states it, and must never be the only thing that does.
 *
 * ADR-601 D4 — two facts are rendered from FIELDS the server sends, never
 * inferred: `kernel` (yarnnn authored this being, so its character is not
 * editable — shown so the distinction is legible before the first
 * member-authored being exists) and `homes` (a LIST — one being may serve
 * several desks since ADR-601 D1, so "Editor — Text, Blogger" reads directly
 * instead of one-to-one being inferred from silence).
 *
 * Server-driven, deliberately: the roster comes from `lanes.list().beings`,
 * which the API builds from the SAME registry the prompt uses. The previous
 * version hardcoded "Designer in Slides, Editor in Text, Keeper in Strings"
 * in prose — a fourth being would silently never have appeared (the ADR-562
 * second-home failure, in copy rather than in code).
 */

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Archive, ArrowLeft, Bot, ClipboardList, Palette, PenTool } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

// The registry's `icon` is a kebab-case lucide name (ADR-460 row shape).
// Mapped explicitly rather than resolved dynamically: lucide's dynamic import
// pulls the whole icon set into the bundle, and a being whose icon is missing
// should render the neutral fallback, not crash the surface. `AgentIcon` is
// NOT reused — it keys off the pre-ADR-596 ROLE taxonomy, not a being's slug.
// One entry per `icon` value in api/services/agents_registry.AGENTS. A being
// whose icon is missing here renders the fallback Bot glyph — silently, and
// looking like every other unmapped being. Supervisor did exactly that until
// 2026-08-26: the registry said `clipboard-list`, this map had three keys.
// A being's glyph is part of how the member tells one desk from another, so a
// miss is a real defect, not a cosmetic one. Add the row when the registry does.
const ICONS: Record<string, React.ElementType> = {
  'pen-tool': PenTool,             // authoring — decks and prose (ADR-602 D4)
  palette: Palette,                // generation — the metered pipeline
  'clipboard-list': ClipboardList, // the standing declaration — Supervisor's desk
  archive: Archive,                // maintenance — a designated file kept true
};

// Provenance, rendered from the field. A member-authored being simply lacks
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

// The desks a being works at, in the member's vocabulary. Prefers the served
// titles and falls back to the slugs, so a backend that predates `home_titles`
// still renders a being's desks rather than an empty line.
function homeNames(being: { homes: string[]; home_titles?: string[] }): string[] {
  return being.home_titles?.length ? being.home_titles : being.homes;
}

function BeingIcon({ icon }: { icon: string }) {
  const Glyph = ICONS[icon] ?? Bot;
  return <Glyph className="h-4 w-4 text-muted-foreground" />;
}

type Being = {
  slug: string;
  name: string;
  blurb: string;
  icon: string;
  offered: boolean;
  kernel: boolean;
  /** The desks this being works at, as ROUTING KEYS. Kept for addressing. */
  homes: string[];
  /** The same desks as the member READS them — the app's declared title.
   *  Render this one; `homes` is an address, and an address is not a name. */
  home_titles?: string[];
  /** The engine behind the name (ADR-460 D4). Served so the page can say what
   *  actually runs this being rather than implying it. */
  model?: string;
};

/** One being's page. Read-only for a kernel being — stated, not merely
 *  unbuilt (ADR-601 D3's chokepoint is the enforcement; this is the telling). */
function BeingDetail({ being, onBack }: { being: Being; onBack: () => void }) {
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
          <BeingIcon icon={being.icon} />
        </div>
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <h1 className="text-sm font-medium">{being.name}</h1>
            {being.kernel && <KernelMark />}
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {being.blurb}
          </p>
        </div>
      </header>

      <dl className="space-y-3 text-xs">
        <div className="flex gap-3">
          <dt className="w-24 shrink-0 text-muted-foreground">Works in</dt>
          <dd>{homeNames(being).length ? homeNames(being).join(', ') : 'Anywhere you invite them'}</dd>
        </div>
        <div className="flex gap-3">
          <dt className="w-24 shrink-0 text-muted-foreground">Add to a chat</dt>
          <dd>
            {being.offered
              ? 'Yes — bring them into any conversation.'
              : 'No — you find them in their app.'}
          </dd>
        </div>
        {being.model && (
          <div className="flex gap-3">
            <dt className="w-24 shrink-0 text-muted-foreground">Runs on</dt>
            <dd className="break-all">{being.model}</dd>
          </div>
        )}
        <div className="flex gap-3">
          <dt className="w-24 shrink-0 text-muted-foreground">Editing</dt>
          <dd>
            {being.kernel
              ? 'Comes with yarnnn — this one can\u2019t be changed.'
              : 'Yours — you can change this one.'}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function AgentsSurface() {
  const params = useSearchParams();
  const { setSurfaceParams } = useSurfacePreferences();
  const [beings, setBeings] = useState<Being[] | null>(null);
  // Read UNPREFIXED: the shell owns the `agents.` namespacing on the way in
  // and out (surface-preferences), and a surface reads its own key plainly —
  // the SettingsPaneShell `tab` precedent.
  const selectedSlug = params.get('agent') || '';
  const selected = (beings ?? []).find((b) => b.slug === selectedSlug) ?? null;

  // The crumb follows the depth, so the address bar and the trail agree.
  useWindowCrumb('agents', selected ? [{ label: selected.name }] : []);

  // `setSurfaceParams`, never a pathname flip: the shell's foreground effects
  // branch on the `/desktop` baseline, and a flip here trips all three
  // (surface-preferences §depth). null clears the key — back to the list.
  const open = (slug: string | null) => setSurfaceParams({ agent: slug });

  useEffect(() => {
    let alive = true;
    api.lanes
      .list(true)
      .then((res) => {
        if (alive) setBeings((res.beings ?? []) as Being[]);
      })
      // A failed read must not render as "you have nobody" — that is the exact
      // false statement this surface exists to stop telling.
      .catch(() => alive && setBeings(null));
    return () => {
      alive = false;
    };
  }, []);

  const housed = (beings ?? []).filter((b) => !b.offered);
  const offered = (beings ?? []).filter((b) => b.offered);

  if (selected) {
    return (
      <div className="h-full overflow-y-auto px-6 py-8">
        <BeingDetail being={selected} onBack={() => open(null)} />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-2xl space-y-8">
        <header className="space-y-1">
          <h1 className="text-sm font-medium">Agents</h1>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Who works with you here. Some are part of an app — you find them
            there. Others you can bring into a chat.
          </p>
        </header>

        <section className="space-y-3">
          <h2 className="text-xs font-medium text-muted-foreground">
            In an app
          </h2>
          {housed.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              {beings === null
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
                    <BeingIcon icon={b.icon} />
                  </div>
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <span className="text-sm font-medium">{b.name}</span>
                      {homeNames(b).length > 0 && (
                        <span className="text-[11px] text-muted-foreground">
                          in {homeNames(b).join(', ')}
                        </span>
                      )}
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

        <section className="space-y-3">
          <h2 className="text-xs font-medium text-muted-foreground">
            To work with
          </h2>
          {offered.length === 0 ? (
            <div className="flex items-start gap-3 rounded-lg border border-dashed border-border/60 p-4">
              <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-muted">
                <Bot className="h-4 w-4 text-muted-foreground" />
              </div>
              {/* ADR-602 D5 — plain language. The prior copy said "roster of
                  colleagues … agent-and-app scaffolding settles (ADR-599)":
                  an ADR number is an internal address, and a member reading
                  it learns nothing they can act on. */}
              <p className="text-xs text-muted-foreground leading-relaxed">
                Nobody yet — you&rsquo;ll be able to add your own here later.
              </p>
            </div>
          ) : (
            <ul className="space-y-2">
              {offered.map((b) => (
                <li key={b.slug}>
                  <button
                    type="button"
                    onClick={() => open(b.slug)}
                    className="flex w-full items-start gap-3 rounded-lg border border-border/60 p-3 text-left transition-colors hover:bg-muted/50"
                  >
                  <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-muted">
                    <BeingIcon icon={b.icon} />
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
      </div>
    </div>
  );
}
