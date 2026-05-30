'use client';

/**
 * AuthorCorpus — alpha-author program section (order: 2 per SURFACES.yaml).
 *
 * Ground-truth substrate face — alpha-author's _signal.md instance per
 * FOUNDATIONS Axiom 8 (Ground-Truth Substrate, post-ADR-282) + ADR-283
 * step 2 substrate enrichment. Multi-signal with graceful degradation:
 *   - Internal coherence (always present): voice/continuity audit
 *     accuracy + entity-continuity accuracy from rolling windows.
 *   - Audience signal: empty by design (alpha-author ships no audience
 *     capabilities per ADR-283 D7 + Discovery note 2).
 *   - External outcomes: operator-authored sparse events (manuscript
 *     accepted, optioned, published, cited, etc.) when present.
 *
 * Per ADR-245 three-layer model: L3 structured affordance that parses
 * _signal.md frontmatter as YAML directly (no shared L2 parser exists
 * for this shape — the schema is bundle-specific). Approach A —
 * substrate-read only.
 *
 * Empty state: _signal.md does not exist until outcome-reconciliation
 * has fired at least once. Pre-first-reconciliation workspaces see a
 * bootstrap message explaining the calibration cycle hasn't started.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, Activity, FileWarning, BookOpen } from 'lucide-react';
import { api } from '@/lib/api/client';

const SIGNAL_PATH = '/workspace/context/authored/_signal.md';
const ENTITIES_PATH = '/workspace/context/authored/_entities.md';

interface RollingWindow {
  audits_total?: number;
  audits_approved?: number;
  audits_deferred?: number;
  audits_rejected?: number;
  pieces_shipped?: number;
  voice_flags_total?: number;
  voice_flags_correct?: number;
  voice_flags_false_positive?: number;
  continuity_flags_total?: number;
  continuity_flags_correct?: number;
  continuity_flags_false_positive?: number;
  cadence_state?: 'on-cadence' | 'behind' | 'ahead';
}

interface ExternalOutcome {
  event_type?: string;
  occurred_at?: string;
  recorded_at?: string;
  piece_slug?: string | null;
  source?: string;
  note?: string;
  impact?: 'high' | 'medium' | 'low';
}

interface SignalFrontmatter {
  last_reconciled?: string;
  rolling_windows?: {
    '7d'?: RollingWindow;
    '30d'?: RollingWindow;
    '90d'?: RollingWindow;
  };
  external_outcomes?: ExternalOutcome[];
  calibration?: {
    voice_audit_accuracy_30d?: number;
    continuity_audit_accuracy_30d?: number;
    entity_continuity_accuracy_30d?: number;
  };
}

interface EntityIndex {
  entityCount: number;
}

function parseFrontmatter(content: string): SignalFrontmatter | null {
  // Hand-rolled YAML extraction matching the FE convention (no js-yaml
  // dependency; see web/lib/content-shapes/autonomy.ts for the same
  // line-based pattern). The _signal.md schema is bundle-specific and
  // tolerantly parsed — missing fields degrade gracefully via the
  // optional-chained reads in the render path.
  const m = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!m) return null;

  const result: SignalFrontmatter = {};
  const lines = m[1].split('\n');

  // Tracking state for nested sections we care about
  type WindowKey = '7d' | '30d' | '90d';
  let currentTop: string | null = null;
  let currentWindow: WindowKey | null = null;
  let inExternalOutcomes = false;
  let currentOutcome: ExternalOutcome | null = null;

  const numericKeys = new Set([
    'audits_total', 'audits_approved', 'audits_deferred', 'audits_rejected',
    'pieces_shipped', 'voice_flags_total', 'voice_flags_correct',
    'voice_flags_false_positive', 'continuity_flags_total',
    'continuity_flags_correct', 'continuity_flags_false_positive',
    'voice_audit_accuracy_30d', 'continuity_audit_accuracy_30d',
    'entity_continuity_accuracy_30d',
  ]);

  const setWindowField = (window: RollingWindow, k: string, raw: string) => {
    const v = raw.trim().replace(/^['"]|['"]$/g, '').replace(/\s*#.*$/, '').trim();
    if (numericKeys.has(k)) {
      const n = Number(v);
      if (!Number.isNaN(n)) (window as Record<string, unknown>)[k] = n;
    } else if (k === 'cadence_state') {
      (window as Record<string, unknown>)[k] = v as RollingWindow['cadence_state'];
    }
  };

  for (const rawLine of lines) {
    if (/^\s*#/.test(rawLine) || /^\s*$/.test(rawLine)) continue;
    const indent = rawLine.match(/^(\s*)/)?.[1].length ?? 0;

    // Top-level keys
    if (indent === 0) {
      const topMatch = rawLine.match(/^([a-z_]+):\s*(.*)$/);
      if (topMatch) {
        currentTop = topMatch[1];
        currentWindow = null;
        inExternalOutcomes = currentTop === 'external_outcomes';
        if (inExternalOutcomes) result.external_outcomes = [];
        if (currentTop === 'rolling_windows' && !result.rolling_windows) result.rolling_windows = {};
        if (currentTop === 'calibration' && !result.calibration) result.calibration = {};
        const value = topMatch[2].trim().replace(/^['"]|['"]$/g, '').replace(/\s*#.*$/, '').trim();
        if (currentTop === 'last_reconciled' && value) result.last_reconciled = value;
        continue;
      }
    }

    // 2-space indent inside rolling_windows: window keys (7d / 30d / 90d)
    if (currentTop === 'rolling_windows' && indent === 2) {
      const winMatch = rawLine.match(/^\s{2}(['"]?)([0-9]+d)\1:\s*$/);
      if (winMatch) {
        const candidate = winMatch[2];
        if (candidate === '7d' || candidate === '30d' || candidate === '90d') {
          currentWindow = candidate;
          if (result.rolling_windows) result.rolling_windows[candidate] = {};
        } else {
          currentWindow = null;
        }
        continue;
      }
    }

    // 4-space indent inside a rolling-window block: field assignments
    if (currentTop === 'rolling_windows' && currentWindow && indent === 4) {
      const fieldMatch = rawLine.match(/^\s{4}([a-z_]+):\s*(.*)$/);
      const win = result.rolling_windows?.[currentWindow];
      if (fieldMatch && win) {
        setWindowField(win, fieldMatch[1], fieldMatch[2]);
        continue;
      }
    }

    // 2-space indent inside calibration: numeric fields
    if (currentTop === 'calibration' && indent === 2) {
      const calMatch = rawLine.match(/^\s{2}([a-z_]+):\s*(.*)$/);
      if (calMatch && result.calibration) {
        const k = calMatch[1];
        const v = calMatch[2].trim().replace(/^['"]|['"]$/g, '').replace(/\s*#.*$/, '').trim();
        if (numericKeys.has(k)) {
          const n = Number(v);
          if (!Number.isNaN(n)) (result.calibration as Record<string, unknown>)[k] = n;
        }
        continue;
      }
    }

    // external_outcomes: list of {event_type, occurred_at, ...}
    if (inExternalOutcomes && result.external_outcomes) {
      // List item start: `  - event_type: ...`
      const listStart = rawLine.match(/^\s{2}-\s+([a-z_]+):\s*(.*)$/);
      if (listStart) {
        if (currentOutcome) result.external_outcomes.push(currentOutcome);
        currentOutcome = {};
        const v = listStart[2].trim().replace(/^['"]|['"]$/g, '').replace(/\s*#.*$/, '').trim();
        (currentOutcome as Record<string, unknown>)[listStart[1]] = v;
        continue;
      }
      // Continuation field inside the current list item: `    key: value`
      const contMatch = rawLine.match(/^\s{4}([a-z_]+):\s*(.*)$/);
      if (contMatch && currentOutcome) {
        const v = contMatch[2].trim().replace(/^['"]|['"]$/g, '').replace(/\s*#.*$/, '').trim();
        (currentOutcome as Record<string, unknown>)[contMatch[1]] = v;
        continue;
      }
    }
  }

  if (currentOutcome && result.external_outcomes) {
    result.external_outcomes.push(currentOutcome);
  }

  return result;
}

function parseEntityIndex(content: string): EntityIndex {
  // _entities.md frontmatter declares entity_count + body has ## {slug}
  // entries under "## Entity index". We count entries that aren't the
  // template placeholder shape.
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  let declaredCount = 0;
  if (fm) {
    const countMatch = fm[1].match(/entity_count:\s*(\d+)/);
    if (countMatch) declaredCount = parseInt(countMatch[1], 10);
  }
  return { entityCount: declaredCount };
}

function formatPct(value: number | undefined): string {
  if (value === undefined || value === null) return '—';
  return `${Math.round(value * 100)}%`;
}

function formatRelativeAsOf(iso: string | undefined): string {
  if (!iso) return 'never';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'unknown';
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

export function AuthorCorpus() {
  const [signal, setSignal] = useState<SignalFrontmatter | null>(null);
  const [entities, setEntities] = useState<EntityIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [signalMissing, setSignalMissing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [signalFile, entitiesFile] = await Promise.all([
          api.workspace.getFile(SIGNAL_PATH).catch(() => null),
          api.workspace.getFile(ENTITIES_PATH).catch(() => null),
        ]);
        if (cancelled) return;

        if (!signalFile?.content) {
          setSignalMissing(true);
        } else {
          setSignal(parseFrontmatter(signalFile.content));
        }
        if (entitiesFile?.content) {
          setEntities(parseEntityIndex(entitiesFile.content));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <section aria-label="Corpus signal" className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }

  if (signalMissing) {
    return (
      <section aria-label="Corpus signal" className="rounded-lg border border-border bg-card p-5">
        <div className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
          Corpus signal
        </div>
        <div className="flex items-start gap-3 rounded-md bg-muted/40 p-4 text-sm">
          <FileWarning className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <div>
            <div className="font-medium">Calibration cycle not started</div>
            <div className="mt-1 text-muted-foreground">
              `_signal.md` populates after the first `outcome-reconciliation` recurrence fires.
              The first pre-ship-audit on a real draft seeds the rolling-window data.
            </div>
          </div>
        </div>
      </section>
    );
  }

  const w30 = signal?.rolling_windows?.['30d'];
  const externalOutcomes = signal?.external_outcomes ?? [];
  const recentOutcomes = externalOutcomes.slice(-3).reverse();

  return (
    <section aria-label="Corpus signal" className="rounded-lg border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Corpus signal
        </span>
        <span className="text-muted-foreground/60">
          internal-coherence · reconciled {formatRelativeAsOf(signal?.last_reconciled)}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
            Audits (30d)
          </div>
          <div className="text-2xl font-semibold tabular-nums">
            {w30?.audits_total ?? 0}
          </div>
          <div className="mt-1 text-sm text-muted-foreground">
            {w30?.pieces_shipped ?? 0} shipped
          </div>
        </div>
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
            Voice accuracy
          </div>
          <div className="text-2xl font-semibold tabular-nums">
            {formatPct(signal?.calibration?.voice_audit_accuracy_30d)}
          </div>
          <div className="mt-1 text-sm text-muted-foreground">flag-correct rate</div>
        </div>
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
            Entities
          </div>
          <div className="flex items-center gap-2 text-2xl font-semibold tabular-nums">
            <BookOpen className="h-5 w-5 text-muted-foreground" />
            {entities?.entityCount ?? 0}
          </div>
          <div className="mt-1 text-sm text-muted-foreground">declared</div>
        </div>
      </div>

      {recentOutcomes.length > 0 && (
        <div className="mt-4 border-t border-border pt-3">
          <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/60">
            Recent external outcomes
          </div>
          <ul className="space-y-1 text-sm">
            {recentOutcomes.map((o, i) => (
              <li key={i} className="flex items-start gap-2">
                <Activity className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span>
                  <span className="font-medium">{o.event_type}</span>
                  {o.piece_slug && <span className="text-muted-foreground"> on {o.piece_slug}</span>}
                  {o.note && <span className="text-muted-foreground"> — {o.note}</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs">
        <span className="text-muted-foreground/70">
          Audience signal: <span className="text-muted-foreground">internal-coherence only</span>
        </span>
        <Link
          href={`/context?path=${encodeURIComponent(SIGNAL_PATH)}`}
          className="text-muted-foreground/70 hover:text-foreground hover:underline"
        >
          Open signal →
        </Link>
      </div>
    </section>
  );
}
