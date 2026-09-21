'use client';

/**
 * The shell layout's wait label (ADR-661 §8 step 4).
 *
 * A Suspense fallback must render synchronously, so the web layout resolves
 * `t('loading')` on the server and passes the string down. The shell has no
 * server, so the word is read with the hook instead — which is legal here
 * because this renders inside `ShellIntlScope`, mounted above the boundary.
 *
 * Its own file because a `'use client'` component cannot be declared in a
 * server layout module, and the shell layout must stay a server component
 * (Next requires a layout to be one unless it opts out, and opting out would
 * pull the whole tree client-side at the root).
 */

import { useTranslations } from 'next-intl';
import { Working } from '@/components/shared/Working';

export function FallbackWait() {
  const t = useTranslations('shell');
  return <Working label={t('loading')} className="text-sm" />;
}
