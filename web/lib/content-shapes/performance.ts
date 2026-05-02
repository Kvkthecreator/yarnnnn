/**
 * Performance content shape — `_performance.md` + `_performance_summary.md`.
 *
 * NEW shape entry added by ADR-245 Phase 2. Parser extracted from
 * `MoneyTruthFace.tsx` inline `parseFrontmatter` (ADR-228 substrate path).
 * Phase 3 audit will refactor `MoneyTruthFace` to import from this module.
 *
 * Per ADR-245 D5 the WRITE_CONTRACT is `live_aggregate` — only the system
 * outcomes ledger (`api/services/outcomes/ledger.py` per ADR-195 v2)
 * writes; operators never edit through L3. The canonical L3
 * (MoneyTruthFace) renders parsed metrics + `last reconciled` link to the
 * raw substrate as escape hatch.
 */

import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'performance' as const;
export const PATH_GLOB = '**/context/{*/_performance.md,_performance_summary.md}';
export const WRITE_CONTRACT = 'live_aggregate' as const;
export const CANONICAL_L3 = 'MoneyTruthFace' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Types — match the frontmatter shape `outcomes/ledger.py` writes
// ---------------------------------------------------------------------------

export interface PerformanceMeta {
  pnl_30d_pct?: number;
  pnl_30d_target_pct?: number;
  drawdown_30d_pct?: number;
  drawdown_limit_pct?: number;
  exposure_pct?: number;
  exposure_limit_pct?: number;
  win_rate?: number;
  generated_at?: string;
}

// ---------------------------------------------------------------------------
// Pure parser — extracted from MoneyTruthFace.tsx inline parser
// ---------------------------------------------------------------------------

export function parse(content: string): PerformanceMeta {
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fm) return {};
  const meta: PerformanceMeta = {};
  for (const line of fm[1].split('\n')) {
    const m = line.match(/^([a-z_0-9]+):\s*(.*)$/);
    if (!m) continue;
    const k = m[1].trim();
    const v = m[2].trim().replace(/^['"]|['"]$/g, '');
    const num = Number(v);
    if (!Number.isNaN(num)) {
      if (k === 'pnl_30d_pct') meta.pnl_30d_pct = num;
      if (k === 'pnl_30d_target_pct') meta.pnl_30d_target_pct = num;
      if (k === 'drawdown_30d_pct' || k === 'max_drawdown_30d_pct') {
        meta.drawdown_30d_pct = num;
      }
      if (k === 'drawdown_limit_pct') meta.drawdown_limit_pct = num;
      if (k === 'exposure_pct') meta.exposure_pct = num;
      if (k === 'exposure_limit_pct') meta.exposure_limit_pct = num;
      if (k === 'win_rate') meta.win_rate = num;
    } else if (k === 'generated_at') {
      meta.generated_at = v;
    }
  }
  return meta;
}
