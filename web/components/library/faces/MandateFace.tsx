'use client';

/**
 * MandateFace — face #1 of the four-face cockpit (ADR-228).
 *
 * Renders the operator's standing intent and autonomy posture as a single
 * dense face. This is what the operator walked up to ask: "what is this
 * workspace for, and what am I letting it do on my behalf?"
 *
 * Sources:
 *   - /workspace/context/_shared/MANDATE.md (ADR-207) — standing intent
 *   - /workspace/context/_shared/AUTONOMY.md (ADR-217) — autonomy posture
 *   - active bundle's MANIFEST.yaml — current_phase, phase label
 *
 * Skeleton state: when MANDATE is absent, the face renders destructive-tinted
 * with a single CTA to author. The other faces still render — the operator
 * is allowed to look at platform balance and recent activity even when
 * mandate is incomplete; what they cannot do without mandate is fairly
 * judge whether the operation is on track.
 *
 * Bundle override surface: the autonomy summary formatter (e.g., trader's
 * "Bounded autonomy on paper · $100/$500 day budget remaining") is bundle-
 * supplied. Kernel default reads `domains.default.level` from AUTONOMY.md
 * frontmatter and renders that label only.
 */

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { Compass } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useComposition } from '@/lib/compositor';
import {
  AUTONOMY_PATH,
  parseAutonomy,
  parseRoundTrip as parseAutonomyRoundTrip,
  serialize as serializeAutonomy,
  type AutonomyLevel,
  type AutonomyMeta,
} from '@/lib/content-shapes/autonomy';
import { writeShape } from '@/lib/content-shapes/write';
import { useCockpit } from '../CockpitContext';

const MANDATE_PATH = '/workspace/context/_shared/MANDATE.md';

interface MandateMeta {
  primary_action?: string;
  posture?: string;
  cadence?: string;
}

/**
 * Strip markdown noise from a line: blockquote prefixes, HTML comments,
 * trailing whitespace. Returns null if the line is decorative-only after
 * stripping.
 */
function stripLine(raw: string): string | null {
  let line = raw.replace(/^\s*>+\s?/, '').trim();
  if (!line) return null;
  // Skip pure HTML comments
  if (line.startsWith('<!--') && line.endsWith('-->')) return null;
  // Skip horizontal rules
  if (/^[-*_]{3,}$/.test(line)) return null;
  return line;
}

function parseMandate(content: string): {
  meta: MandateMeta;
  intent: string[];
  isSkeleton: boolean;
} {
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  const meta: MandateMeta = {};
  let body = content;
  if (fm) {
    body = content.slice(fm[0].length);
    for (const line of fm[1].split('\n')) {
      const m = line.match(/^([a-z_]+):\s*(.*)$/);
      if (!m) continue;
      const k = m[1].trim();
      const v = m[2].trim().replace(/^['"]|['"]$/g, '');
      if (k === 'primary_action') meta.primary_action = v;
      if (k === 'posture') meta.posture = v;
      if (k === 'cadence') meta.cadence = v;
    }
  }
  const trimmed = body.trim();
  const isSkeleton =
    !trimmed ||
    /^#\s*MANDATE\s*$/i.test(trimmed) ||
    /^_authored at workspace activation/i.test(trimmed);

  // Walk past leading headings + comments, collect prose paragraph
  // (consecutive non-blank, non-heading lines) for the intent block.
  const lines = body.split('\n');
  const intentLines: string[] = [];
  let inBlock = false;
  for (const raw of lines) {
    const t = raw.trim();
    if (!t) {
      if (inBlock) break; // blank line ends the first prose block
      continue;
    }
    if (t.startsWith('#')) {
      if (inBlock) break;
      continue;
    }
    if (t.startsWith('---')) continue;
    const stripped = stripLine(raw);
    if (!stripped) {
      if (inBlock) break;
      continue;
    }
    intentLines.push(stripped);
    inBlock = true;
  }
  return { meta, intent: intentLines, isSkeleton };
}

// `parseAutonomy` + `AutonomyMeta` lifted to `@/lib/content-shapes/autonomy`
// by ADR-238 (parser) and ADR-244 Phase 2 (registry home). Singular
// Implementation: do not re-inline here. ADR-244 Phase 4 adds mutation —
// the autonomy posture is now operator-toggleable from this face,
// making MandateFace the canonical L3 for the autonomy content shape
// per ADR-244 D4.

const AUTONOMY_LEVELS: ReadonlyArray<{ value: AutonomyLevel; label: string }> = [
  { value: 'manual', label: 'Manual' },
  { value: 'assisted', label: 'Assisted' },
  { value: 'bounded_autonomous', label: 'Bounded autonomous' },
  { value: 'autonomous', label: 'Autonomous' },
];

interface AutonomyToggleProps {
  raw: string;
  onWritten: (newContent: string) => void;
}

function AutonomyToggle({ raw, onWritten }: AutonomyToggleProps) {
  const { meta, body } = parseAutonomyRoundTrip(raw);
  const currentLevel = (meta.default_level as AutonomyLevel | undefined) ?? null;
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = useCallback(
    async (e: React.ChangeEvent<HTMLSelectElement>) => {
      const next = e.target.value as AutonomyLevel;
      if (next === currentLevel) return;
      const nextMeta: AutonomyMeta = { ...meta, default_level: next };
      const serialized = serializeAutonomy(nextMeta, body);
      setPending(true);
      setError(null);
      try {
        await writeShape('autonomy', AUTONOMY_PATH, serialized, {
          message: `autonomy posture: default → ${next}`,
        });
        onWritten(serialized);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to write autonomy');
      } finally {
        setPending(false);
      }
    },
    [meta, body, currentLevel, onWritten],
  );

  return (
    <span className="inline-flex items-center gap-1.5">
      <select
        value={currentLevel ?? ''}
        onChange={handleChange}
        disabled={pending}
        aria-label="Autonomy posture"
        className="rounded-sm border border-border bg-card px-1.5 py-0.5 text-[11px] font-medium text-foreground hover:border-foreground/40 focus:outline-none focus:ring-1 focus:ring-foreground/40 disabled:opacity-50"
      >
        {currentLevel === null && <option value="">No autonomy declared</option>}
        {AUTONOMY_LEVELS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <span className="text-[10px] text-destructive" title={error}>
          ⚠ failed
        </span>
      )}
    </span>
  );
}

export function MandateFace() {
  const { onOpenChatDraft } = useCockpit();
  const { data: composition } = useComposition();
  const phase = composition.active_bundles[0]?.current_phase_label ?? null;

  const [mandate, setMandate] = useState<string | null>(null);
  const [autonomy, setAutonomy] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [mandateR, autonomyR] = await Promise.allSettled([
        api.workspace.getFile(MANDATE_PATH),
        api.workspace.getFile(AUTONOMY_PATH),
      ]);
      if (cancelled) return;
      setMandate(mandateR.status === 'fulfilled' ? mandateR.value?.content ?? '' : '');
      setAutonomy(autonomyR.status === 'fulfilled' ? autonomyR.value?.content ?? '' : '');
      setLoaded(true);
    })();
    return () => { cancelled = true; };
  }, []);

  const handleAutonomyWritten = useCallback((newContent: string) => {
    setAutonomy(newContent);
  }, []);

  if (!loaded) return null;

  const { meta, intent, isSkeleton } = parseMandate(mandate ?? '');
  const autonomyMeta = parseAutonomy(autonomy ?? '');
  const ceiling =
    autonomyMeta.default_ceiling_cents ??
    Object.values(autonomyMeta.domains ?? {})[0]?.ceiling_cents ??
    null;
  const ceilingSuffix = ceiling && ceiling > 0 ? ` · ceiling $${(ceiling / 100).toLocaleString()}` : '';

  if (isSkeleton) {
    return (
      <section
        aria-label="Mandate"
        className="rounded-lg border-2 border-amber-300 bg-amber-50/60 p-5"
      >
        <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-amber-900">
          <Compass className="h-3.5 w-3.5" />
          Mandate
        </div>
        <p className="mb-3 text-sm font-medium text-amber-900">
          Delegation contract incomplete — author your mandate before relying on
          the operation.
        </p>
        <p className="mb-4 text-xs text-amber-900/80">
          Mandate declares what this workspace is for: the primary action you've
          delegated, the success criteria, and the boundaries you want enforced.
          Autonomy declares what the system is permitted to do without your
          approval. Both are read at every cockpit load.
        </p>
        <button
          onClick={() =>
            onOpenChatDraft(
              "Help me author my workspace MANDATE.md — what should my Primary Action be?",
            )
          }
          className="rounded-md bg-amber-900 px-3 py-1.5 text-xs font-medium text-amber-50 hover:bg-amber-900/90"
        >
          Draft mandate in chat →
        </button>
      </section>
    );
  }

  const tags: string[] = [];
  if (meta.posture) tags.push(meta.posture);
  if (meta.cadence) tags.push(meta.cadence);

  return (
    <section
      aria-label="Mandate"
      className="rounded-lg border border-border bg-card p-5"
    >
      <div className="mb-3 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Mandate
        </span>
        <span className="flex items-center gap-1.5 text-muted-foreground/60">
          {phase && <span>{phase}</span>}
          {phase && <span aria-hidden="true">·</span>}
          {autonomy ? (
            <>
              <AutonomyToggle raw={autonomy} onWritten={handleAutonomyWritten} />
              {ceilingSuffix && <span>{ceilingSuffix}</span>}
            </>
          ) : (
            <span>No autonomy declared</span>
          )}
        </span>
      </div>
      <Link
        href={`/context?path=${encodeURIComponent(MANDATE_PATH)}`}
        className="block"
      >
        {meta.primary_action ? (
          <p className="text-base font-medium leading-snug text-foreground hover:underline">
            {meta.primary_action}
          </p>
        ) : intent.length > 0 ? (
          <div className="space-y-1 text-sm leading-relaxed text-foreground hover:underline">
            {intent.slice(0, 4).map((line, idx) => (
              <p key={idx}>{line}</p>
            ))}
          </div>
        ) : (
          <p className="text-base font-medium leading-snug text-foreground hover:underline">
            Mandate authored
          </p>
        )}
      </Link>
      {tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-muted-foreground">
          {tags.map((tag) => (
            <span key={tag} className="rounded-sm bg-muted px-1.5 py-0.5">
              {tag}
            </span>
          ))}
        </div>
      )}
      <div className="mt-4 flex gap-3 text-[11px] text-muted-foreground/70">
        <Link
          href={`/context?path=${encodeURIComponent(MANDATE_PATH)}`}
          className="underline-offset-4 hover:text-foreground hover:underline"
        >
          MANDATE.md
        </Link>
        <Link
          href={`/context?path=${encodeURIComponent(AUTONOMY_PATH)}`}
          className="underline-offset-4 hover:text-foreground hover:underline"
        >
          AUTONOMY.md
        </Link>
      </div>
    </section>
  );
}
