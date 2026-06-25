'use client';

/**
 * HomeRenderer — renamed from CockpitRenderer by ADR-312 D1; six-slot
 * composition wired 2026-06-04 (ADR-312 D2 amendment); made an OPERATING
 * COCKPIT (acts in place) by ADR-367; SPLIT INTO TWO TABS by ADR-369.
 *
 * ADR-369 — the Home split. ADR-312 D1 unified the cockpit into ONE Home
 * composition; ADR-369 consciously reverses that unification and re-splits the
 * single `home` surface into two internal tabs via a segmented control, along
 * the **kernel-shaped vs program-shaped** seam (the layout/component seam the
 * code already drew — HomeRenderer renders the kernel-universal slots; the
 * program declares `home.program_sections`):
 *
 *   - "Home" (default) — the kernel-shaped front page (HomeFrontPage): the
 *     constitution band + decision queue (acts in place) + visual recents +
 *     recent artifacts + judgment trail. Identical for every workspace — the
 *     most learnable default.
 *   - "‹Program›" — the program-shaped operating cockpit (ProgramCockpit): the
 *     relocated standing band + the program's ground-truth hero/entities. The
 *     tab is ADDITIVE — it renders ONLY when a program is active, labeled by the
 *     active program's MANIFEST title (ADR-222 — the kernel provides a generic
 *     program-composition tab; the program names + shapes it, no program noun
 *     hardcoded in the kernel). A Layer-1 operator sees only "Home" (ADR-312's
 *     cold-start virtue preserved).
 *
 * Tab state is a window-namespaced param `home.tab ∈ {home, <program-slug>}`
 * (ADR-358 D6; scopeParamKey forms the `home.` prefix), default `home`,
 * SSR-safe (the server renders the default; the post-mount effect applies the
 * param choice — no hydration mismatch). The `home` launcher tile is unchanged
 * (the split is intra-surface, not a new launcher destination).
 *
 * Singular Implementation (ADR-369 §5): the two bodies are extracted (the
 * existing slot components + the shared StandingBand are MOVED, not rebuilt).
 * HomeRenderer keeps the single home-bundle fetch + the activation derivation;
 * it owns only the tab chrome + dispatch.
 */

import { useEffect, useState } from 'react';
import { useComposition, getProgramSections } from '@/lib/compositor';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';
import { HomeProvider } from './HomeContext';
import { HomeFrontPage } from './kernel-home/HomeFrontPage';
import { ProgramCockpit } from './kernel-home/ProgramCockpit';
import { api } from '@/lib/api/client';

type HomeBundle = Awaited<ReturnType<typeof api.workspace.getHomeBundle>>;

const HOME_TAB = 'home';

/**
 * Prettify a program slug/title for the segmented-control label (ADR-369 §D2).
 * The active bundle's MANIFEST `title` is the program's own name (a kebab/snake
 * slug like "my-program"); render it title-cased ("My Program"). The label
 * derives entirely from the program — the kernel hardcodes no program noun
 * (ADR-222). Falls back to the generic "Operation" only if the program declares
 * no title.
 */
function programTabLabel(title: string | null | undefined): string {
  const raw = (title ?? '').trim();
  if (!raw) return 'Operation';
  return raw
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

interface HomeRendererProps {
  /**
   * Chat-draft handler. Forwarded into HomeContext so any home slot
   * component can call sendMessage() without prop-drilling.
   */
  onOpenChatDraft?: (prompt: string) => void;
}

export function HomeRenderer({ onOpenChatDraft }: HomeRendererProps) {
  const handleOpenChatDraft = onOpenChatDraft ?? (() => { /* no-op */ });

  // ADR-312 home-bundle: one call fetches composition + all three
  // kernel-universal slots + the two constitution-band files. We prime every
  // child off this single response; each child keeps its self-fetch fallback
  // for standalone reuse elsewhere.
  const [bundle, setBundle] = useState<HomeBundle | null>(null);
  const [bundleLoaded, setBundleLoaded] = useState(false);
  useEffect(() => {
    let cancelled = false;
    api.workspace
      .getHomeBundle()
      .then((b) => {
        if (!cancelled) setBundle(b);
      })
      .catch(() => {
        // Bundle unreachable: children fall back to self-fetch (no props
        // primed) so the Home never breaks.
      })
      .finally(() => {
        if (!cancelled) setBundleLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Prime the compositor hook from the bundle when present; otherwise it
  // self-fetches (graceful degradation if the bundle call failed).
  const { data: composition } = useComposition(
    bundle ? { initialData: bundle.surfaces } : undefined,
  );
  const programSections = getProgramSections(composition);
  const hasProgramSections = programSections.length > 0;

  // Activation derived from the bundle's composition (active_bundles). The
  // program tab is ADDITIVE: it renders ONLY when a program is active.
  const activeBundle = bundle?.surfaces.active_bundles?.[0] ?? null;
  const activeProgramSlug = activeBundle?.slug ?? null;
  const programTab = activeProgramSlug; // the program tab's param value = its slug
  const programLabel = programTabLabel(activeBundle?.title);
  const showProgramTab = !!activeProgramSlug;

  // The cold-start CTA renders only when there is genuinely nothing to show:
  // no program sections AND no activated bundle.
  const showActivationCTA =
    !hasProgramSections && bundleLoaded && !activeProgramSlug;

  // ADR-369 §D2 — tab state via the window-namespaced param `home.tab`
  // (ADR-358 D6). SSR-safe: initialize to the default 'home' so the server and
  // the first client render agree (no hydration mismatch), then apply the URL
  // param post-mount. Mirrors the deferred-initializer pattern used elsewhere.
  const homeParam = useSurfaceParam(HOME_TAB);
  const [tab, setTab] = useState<string>(HOME_TAB);
  useEffect(() => {
    const t = homeParam.get('tab');
    // Only honor the program tab when a program is actually active; otherwise
    // a stale `home.tab=<slug>` (e.g. after deactivation) falls back to Home.
    if (t && t !== HOME_TAB && t === programTab) {
      setTab(t);
    } else {
      setTab(HOME_TAB);
    }
  }, [homeParam, programTab]);

  // Defensive: if the program tab vanishes (deactivation) while it's selected,
  // snap back to Home.
  const activeTab = showProgramTab && tab === programTab ? programTab : HOME_TAB;

  const selectTab = (next: string) => {
    setTab(next);
    homeParam.set({ tab: next === HOME_TAB ? null : next });
  };

  return (
    <HomeProvider value={{ onOpenChatDraft: handleOpenChatDraft }}>
      <section aria-label="Home" className="border-b border-border/60">
        {/* ADR-369 §D2 — the segmented control. Renders only when there's a
            program tab to switch to; a Layer-1 operator (no program) sees no
            control and just the Home front page. */}
        {showProgramTab && (
          <div
            role="tablist"
            aria-label="Home view"
            className="flex items-center gap-1 border-b border-border/60 px-4 py-2 sm:px-6"
          >
            <TabButton
              label="Home"
              selected={activeTab === HOME_TAB}
              onClick={() => selectTab(HOME_TAB)}
            />
            <TabButton
              label={programLabel}
              selected={activeTab === programTab}
              onClick={() => programTab && selectTab(programTab)}
            />
          </div>
        )}

        {activeTab === programTab && showProgramTab ? (
          <ProgramCockpit programSections={programSections} />
        ) : (
          <HomeFrontPage
            bundle={bundle}
            showActivationCTA={showActivationCTA}
            activeProgramSlug={activeProgramSlug}
          />
        )}
      </section>
    </HomeProvider>
  );
}

function TabButton({
  label,
  selected,
  onClick,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      role="tab"
      type="button"
      aria-selected={selected}
      onClick={onClick}
      className={cn(
        'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
        selected
          ? 'bg-muted text-foreground'
          : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
      )}
    >
      {label}
    </button>
  );
}
