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
import { Archive, FilePen, PenTool, Users } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';

// The registry's `icon` is a kebab-case lucide name (ADR-460 row shape).
// Mapped explicitly rather than resolved dynamically: lucide's dynamic import
// pulls the whole icon set into the bundle, and a being whose icon is missing
// should render the neutral fallback, not crash the surface. `AgentIcon` is
// NOT reused — it keys off the pre-ADR-596 ROLE taxonomy, not a being's slug.
const ICONS: Record<string, React.ElementType> = {
  'pen-tool': PenTool,
  'file-pen': FilePen,
  archive: Archive,
};

// Provenance, rendered from the field. A member-authored being simply lacks
// the mark — there is no "yours" badge, because the member already knows.
function KernelMark() {
  return (
    <span
      className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
      title="A yarnnn system agent — it comes with the apps it works in, so its character is not editable."
    >
      yarnnn
    </span>
  );
}

function BeingIcon({ icon }: { icon: string }) {
  const Glyph = ICONS[icon] ?? Users;
  return <Glyph className="h-4 w-4 text-muted-foreground" />;
}

type Being = {
  slug: string;
  name: string;
  blurb: string;
  icon: string;
  offered: boolean;
  kernel: boolean;
  homes: string[];
};

export function AgentsSurface() {
  useWindowCrumb('agents', []);
  const [beings, setBeings] = useState<Being[] | null>(null);

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

  return (
    <div className="h-full overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-2xl space-y-8">
        <header className="space-y-1">
          <h1 className="text-sm font-medium">Agents</h1>
          <p className="text-xs text-muted-foreground leading-relaxed">
            The colleagues in this workspace. Some work at a desk — you meet
            them in their app. Others you can invite into a conversation.
          </p>
        </header>

        <section className="space-y-3">
          <h2 className="text-xs font-medium text-muted-foreground">
            At a desk
          </h2>
          {housed.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              {beings === null
                ? 'Could not load the roster.'
                : 'No app has a resident yet.'}
            </p>
          ) : (
            <ul className="space-y-2">
              {housed.map((b) => (
                <li
                  key={b.slug}
                  className="flex items-start gap-3 rounded-lg border border-border/60 p-3"
                >
                  <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-muted">
                    <BeingIcon icon={b.icon} />
                  </div>
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <span className="text-sm font-medium">{b.name}</span>
                      {b.homes.length > 0 && (
                        <span className="text-[11px] text-muted-foreground">
                          in {b.homes.join(', ')}
                        </span>
                      )}
                      {b.kernel && <KernelMark />}
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {b.blurb}
                    </p>
                  </div>
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
                <Users className="h-4 w-4 text-muted-foreground" />
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Nobody yet. A roster of colleagues you can invite into a
                conversation, name, and build on will return here once the
                agent-and-app scaffolding settles (ADR-599).
              </p>
            </div>
          ) : (
            <ul className="space-y-2">
              {offered.map((b) => (
                <li
                  key={b.slug}
                  className="flex items-start gap-3 rounded-lg border border-border/60 p-3"
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
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
