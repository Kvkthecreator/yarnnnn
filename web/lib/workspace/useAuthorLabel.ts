'use client';

/**
 * useAuthorLabel — ADR-660. `formatAuthorLabelRef` in `attribution.ts` resolves
 * an `authored_by` slug to a catalog key; this words it.
 *
 * ONE hook for every surface that shows attribution (Files, Recents, the
 * revision panel, the trash, the activity ledger, the boundary ledger, the
 * text editor's conflict banner, the properties panel…). Before this, each
 * surface rendered `formatAuthorLabel`'s English sentence directly, so
 * translating any one of them would have split the vocabulary: one row "나",
 * the next "You".
 */

import { useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  formatAuthorLabelRef,
  formatAuthorLabelRefOrSystem,
} from '@/lib/workspace/attribution';

export function useAuthorLabel() {
  const t = useTranslations('attribution');

  /** The label, or null when there is no attribution to show. */
  const authorLabel = useCallback(
    (authoredBy: string | null | undefined): string | null => {
      const ref = formatAuthorLabelRef(authoredBy);
      return ref ? t(ref.key, ref.args) : null;
    },
    [t],
  );

  /** The label, never null — for glance contexts (Recents, the tree). */
  const authorLabelOrSystem = useCallback(
    (authoredBy: string | null | undefined): string => {
      const ref = formatAuthorLabelRefOrSystem(authoredBy);
      return t(ref.key, ref.args);
    },
    [t],
  );

  return { authorLabel, authorLabelOrSystem };
}
