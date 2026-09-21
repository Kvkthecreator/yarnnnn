'use client';

/**
 * useStructureWords — ADR-660. The structural vocabulary (`Document`, `Group`,
 * `Area`, the frame's noun, the four Area roles), resolved from the catalog.
 *
 * `structureLabels.ts` is the ONE ladder, called from panes and mirrored into
 * the sandboxed canvas runtime. The runtime cannot read a catalog, so the
 * ladder takes RESOLVED words rather than keys — this builds them, and the
 * caller threads them through exactly as `blockLabels` and `__yarnnnFrameNoun`
 * already travel (ADR-544 D4 / ADR-633 D3: one derivation, injected).
 */

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import type { StructureWords } from './structureLabels';

export function useStructureWords(): StructureWords {
  const t = useTranslations('structure');
  return useMemo(
    () => ({
      document: t('document'),
      group: t('group'),
      area: t('area'),
      frameSlide: t('frameSlide'),
      frameArtboard: t('frameArtboard'),
      frameSection: t('frameSection'),
      roles: {
        heading: t('roles.heading'),
        body: t('roles.body'),
        media: t('roles.media'),
        aside: t('roles.aside'),
      },
      areaWithPlace: (role: string, place: string) => t('areaWithPlace', { role, place }),
    }),
    [t],
  );
}
