'use client';

/**
 * AppSurface — ONE component for every member app (ADR-653 D3.c).
 *
 * ⭐⭐⭐ ONE COMPONENT, PARAMETERIZED BY THE DECLARATION. Never one per app,
 * and never a static import per app — that is what keeps the ADR-338 three-way
 * lockstep over KERNEL surfaces untouched: the kernel registry stays a closed
 * union of compile-time imports, and member apps mount through this single
 * generic instead of joining it. An app is DATA here, not code.
 *
 * THE THREE BANDS (APP-BUILDER-UX §2.2). The bands are FIXED; only their
 * contents are declared, and that is the whole reason this is not a page
 * builder:
 *
 *   1. what this is      — the name and the one-line `about`
 *   2. who is minding it — the resident, named
 *   3. the work          — the declared sections (AppSection)
 *
 * ⚠️ THE COST, ACCEPTED (APP-BUILDER-UX §2.3): an app cannot look distinctive.
 * That is the intended trade — distinctiveness is what turns this into a
 * layout engine. What the fixed frame buys: a member learns ONE shape and
 * reads every app anyone makes, and the resident renders in the same place
 * every time rather than being something an app might forget to include.
 *
 * ⚠️ BAND 2 IS THE RESTING STATE ONLY, in this step. APP-BUILDER-UX §4 names
 * three states (resting · working · raising); raising needs the resident read
 * that step 5 builds. *"{Name} looks after this."* is a complete, reassuring
 * sentence — someone is on it and there is nothing to do. It is NOT an empty
 * state, and it must not read like one (compare *"No new activity"*, which
 * says the same thing and sounds like a failure).
 */

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { AppSection, type AppSectionDecl } from '@/components/apps/AppSection';
import { Working } from '@/components/shared/Working';

interface AppDeclaration {
  slug: string;
  name: string;
  about: string;
  agent_name: string;
  sections: AppSectionDecl[];
  declaration_path: string;
}

export function AppSurface({ slug }: { slug: string }) {
  const [decl, setDecl] = useState<AppDeclaration | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    setDecl(null);
    setMissing(false);
    (async () => {
      try {
        const result = await api.apps.get(slug);
        if (cancelled) return;
        setDecl(result);
      } catch {
        // The server withholds an app it cannot draw, so a miss here means
        // the app is gone or was never real. Either way the honest answer is
        // the same, and it is an empty state rather than error chrome
        // (ADR-198 §3).
        if (cancelled) return;
        setMissing(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (missing) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
          This app isn&apos;t set up any more.
        </div>
      </div>
    );
  }
  if (!decl) {
    // ADR-651 — the ONE way to say wait, self-bounding after 6s and 30s.
    return <Working label="Loading…" fill />;
  }

  const sections = Array.isArray(decl.sections) ? decl.sections : [];

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {/* Band 1 — what this is. The visible claim: if it cannot say what the
          app is for, the app is wrong (APP-BUILDER-UX §2.2). */}
      <header className="border-b border-border/60 px-5 py-4">
        <h1 className="text-[15px] font-semibold text-foreground">{decl.name}</h1>
        {decl.about ? (
          <p className="mt-0.5 text-[13px] text-muted-foreground">{decl.about}</p>
        ) : null}
      </header>

      {/* Band 2 — who is minding it. Resting: calm, not absent. */}
      {decl.agent_name ? (
        <div className="border-b border-border/60 bg-muted/20 px-5 py-2.5">
          <p className="text-[13px] text-foreground/80">
            {decl.agent_name} looks after this.
          </p>
        </div>
      ) : null}

      {/* Band 3 — the work. */}
      <div className="flex-1 space-y-5 px-5 py-4">
        {sections.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            Nothing here yet. Files you add to these folders show up here.
          </div>
        ) : (
          sections.map((section, i) => (
            <AppSection key={`${section?.kind}-${i}`} section={section} />
          ))
        )}
      </div>
    </div>
  );
}
