'use client';

/**
 * SurfaceBoundary — the page-level Suspense boundary for a surface that reads
 * `useSearchParams()` (ADR-661 §8 step 3, §7a blocker 4). Found by the static
 * export that ADR-663 later retired; kept because the web's first paint needs
 * it too (below).
 *
 * `useSearchParams()` makes a component read the request's query string. Under
 * SSR that is a dynamic render and Next handles it; under `output: 'export'`
 * there is no request, so the component must be able to bail out to a
 * client-side render — and Next requires a `<Suspense>` boundary to bail out
 * INTO. Without one at the page, the export fails the whole route:
 *
 *   ⨯ useSearchParams() should be wrapped in a suspense boundary at page "/chat"
 *
 * Eight surfaces hit this: chat · files · settings · supervisor · text ·
 * slides · images · notifications. Their consumers were already wrapped "where
 * required" for SSR — which is why reading the code said this was fine, and why
 * only running the export build found it. **A hook that is Suspense-wrapped for
 * SSR is not Suspense-wrapped for export.**
 *
 * This is not export-only scaffolding. The same bailout costs the WEB build a
 * client render on first paint today; the boundary means the member sees the
 * house's one wait (`Working`, ADR-651) instead of nothing while it resolves.
 *
 * WHY ONE COMPONENT AND NOT EIGHT `<Suspense>` TAGS. The fallback is a member-
 * facing state, so eight hand-written ones drift in wording and in shape — the
 * failure class ADR-592 names. `Working` is already "the ONE way to say wait",
 * and it is bounded by construction (it admits slowness, then offers an exit),
 * so a surface that hangs behind this boundary cannot spin for ever.
 *
 * The label rides the catalog (`shell.loading`, ADR-660), so it speaks the
 * member's language. That is also why this is a client component: a Suspense
 * fallback must render synchronously, so it cannot await its own translations
 * — the same constraint `app/(authenticated)/layout.tsx` records for
 * `LayoutFallback`.
 */

import { Suspense } from 'react';
import { useTranslations } from 'next-intl';
import { Working } from '@/components/shared/Working';

function SurfaceFallback() {
  const t = useTranslations('shell');
  return (
    <div className="h-full w-full flex items-center justify-center">
      <Working label={t('loading')} className="text-sm" />
    </div>
  );
}

export function SurfaceBoundary({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<SurfaceFallback />}>{children}</Suspense>;
}
