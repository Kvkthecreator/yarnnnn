'use client';

/**
 * AuthorVoice — alpha-author program section (order: 3 per SURFACES.yaml).
 *
 * Voice consistency face — surfaces:
 *   - Voice fingerprint declaration state (positive markers + anti-patterns
 *     declared count from _voice.md)
 *   - Recent voice-audit findings rolled into _signal.md (voice-flag-rate
 *     30d + top anti-patterns triggered)
 *   - Recent revision attribution per ADR-209 — who's been editing what,
 *     surfaced as "the operator edited content.md 6 times this week;
 *     Reviewer commented on draft-x 2 times" shape
 *
 * Per ADR-245 three-layer model: L3 structured affordance composed from
 * substrate reads — _voice.md content + _signal.md frontmatter
 * (calibration block) + ADR-209 revision listings for context/authored/.
 *
 * Approach A — substrate-read only, no new backend routes.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, Type, AlertCircle, History } from 'lucide-react';
import { api } from '@/lib/api/client';

const VOICE_PATH = '/workspace/context/authored/_voice.md';
const SIGNAL_PATH = '/workspace/context/authored/_signal.md';

interface VoiceFingerprintStats {
  declared: boolean;
  positiveMarkerCount: number;
  antiPatternCount: number;
  hasDeclaredVoice: boolean;
}

interface CalibrationStats {
  voiceAccuracy30d: number | null;
  entityAccuracy30d: number | null;
  voiceFlagsTotal30d: number | null;
}

interface RecentRevision {
  id: string;
  authored_by: string;
  message: string;
  created_at: string;
}

function extractSection(content: string, heading: string): string {
  const re = new RegExp(`##\\s+${heading}\\s*\\n([\\s\\S]*?)(?=\\n##\\s|$)`, 'i');
  const m = content.match(re);
  return m ? m[1].trim() : '';
}

function countMeaningfulBullets(sectionBody: string): number {
  return sectionBody
    .split('\n')
    .map(l => l.trim())
    .filter(l => /^[-*]\s+/.test(l))
    .filter(l => !l.toLowerCase().includes('example shape'))
    .filter(l => !l.startsWith('> '))
    .length;
}

function parseVoiceFingerprint(content: string | undefined): VoiceFingerprintStats {
  if (!content) {
    return { declared: false, positiveMarkerCount: 0, antiPatternCount: 0, hasDeclaredVoice: false };
  }
  const positiveSection = extractSection(content, 'Pattern markers \\(positive\\)');
  const antiSection = extractSection(content, 'Anti-patterns \\(negative\\)');
  const declSection = extractSection(content, 'Declared voice fingerprint');
  const positiveMarkerCount = countMeaningfulBullets(positiveSection);
  const antiPatternCount = countMeaningfulBullets(antiSection);
  const declLines = declSection
    .split('\n')
    .map(l => l.trim())
    .filter(l => l.length > 0)
    .filter(l => !l.startsWith('>'))
    .filter(l => !l.startsWith('#'))
    .filter(l => !/^example shapes?/i.test(l));
  const hasDeclaredVoice = declLines.length >= 2;
  const declared = hasDeclaredVoice || positiveMarkerCount > 0 || antiPatternCount > 0;
  return { declared, positiveMarkerCount, antiPatternCount, hasDeclaredVoice };
}

function parseCalibration(content: string | undefined): CalibrationStats {
  const empty: CalibrationStats = {
    voiceAccuracy30d: null,
    entityAccuracy30d: null,
    voiceFlagsTotal30d: null,
  };
  if (!content) return empty;
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fm) return empty;
  const body = fm[1];
  const voiceMatch = body.match(/voice_audit_accuracy_30d:\s*([0-9.]+)/);
  const entityMatch = body.match(/entity_continuity_accuracy_30d:\s*([0-9.]+)/);
  const flagsMatch = body.match(/^\s+voice_flags_total:\s*(\d+)/m);
  return {
    voiceAccuracy30d: voiceMatch ? parseFloat(voiceMatch[1]) : null,
    entityAccuracy30d: entityMatch ? parseFloat(entityMatch[1]) : null,
    voiceFlagsTotal30d: flagsMatch ? parseInt(flagsMatch[1], 10) : null,
  };
}

function formatPct(value: number | null): string {
  if (value === null) return '—';
  return `${Math.round(value * 100)}%`;
}

function formatRelativeAsOf(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

function shortAuthor(authored_by: string): string {
  // authored_by taxonomy per ADR-209: operator | yarnnn:<model> |
  // reviewer:<identity> | agent:<slug> | system:<actor>
  if (authored_by === 'operator') return 'operator';
  if (authored_by.startsWith('reviewer:')) return 'reviewer';
  if (authored_by.startsWith('yarnnn:')) return 'yarnnn';
  if (authored_by.startsWith('agent:')) return authored_by.slice(6);
  if (authored_by.startsWith('system:')) return 'system';
  return authored_by;
}

export function AuthorVoice() {
  const [voice, setVoice] = useState<VoiceFingerprintStats | null>(null);
  const [calibration, setCalibration] = useState<CalibrationStats | null>(null);
  const [revisions, setRevisions] = useState<RecentRevision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [voiceFile, signalFile, voiceRevisions] = await Promise.all([
          api.workspace.getFile(VOICE_PATH).catch(() => null),
          api.workspace.getFile(SIGNAL_PATH).catch(() => null),
          api.workspace.listRevisions(VOICE_PATH, 5).catch(() => null),
        ]);
        if (cancelled) return;
        setVoice(parseVoiceFingerprint(voiceFile?.content));
        setCalibration(parseCalibration(signalFile?.content));
        setRevisions(voiceRevisions?.revisions ?? []);
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
      <section aria-label="Voice consistency" className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }

  const voiceUndeclared = !voice || !voice.hasDeclaredVoice;

  return (
    <section aria-label="Voice consistency" className="rounded-lg border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Voice consistency
        </span>
        <span className="text-muted-foreground/60">
          per ADR-209 attribution
        </span>
      </div>

      {voiceUndeclared ? (
        <div className="flex items-start gap-3 rounded-md bg-muted/40 p-4 text-sm">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <div>
            <div className="font-medium">Voice fingerprint not yet declared</div>
            <div className="mt-1 text-muted-foreground">
              Open chat to declare your voice in `_voice.md` — the Reviewer reads it
              at every pre-ship-audit. Without it, voice-audit defers to the
              universal anti-slop baseline only.
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
              Pattern markers
            </div>
            <div className="flex items-center gap-2 text-2xl font-semibold tabular-nums">
              <Type className="h-5 w-5 text-muted-foreground" />
              {voice?.positiveMarkerCount ?? 0}
            </div>
            <div className="mt-1 text-sm text-muted-foreground">
              {voice?.antiPatternCount ?? 0} anti-patterns
            </div>
          </div>
          <div>
            <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
              Voice accuracy
            </div>
            <div className="text-2xl font-semibold tabular-nums">
              {formatPct(calibration?.voiceAccuracy30d ?? null)}
            </div>
            <div className="mt-1 text-sm text-muted-foreground">30d audit-correct</div>
          </div>
          <div>
            <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
              Entity accuracy
            </div>
            <div className="text-2xl font-semibold tabular-nums">
              {formatPct(calibration?.entityAccuracy30d ?? null)}
            </div>
            <div className="mt-1 text-sm text-muted-foreground">30d audit-correct</div>
          </div>
        </div>
      )}

      {revisions.length > 0 && (
        <div className="mt-4 border-t border-border pt-3">
          <div className="mb-2 flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground/60">
            <History className="h-3.5 w-3.5" />
            Recent _voice.md revisions
          </div>
          <ul className="space-y-1 text-sm">
            {revisions.slice(0, 3).map(r => (
              <li key={r.id} className="flex items-baseline justify-between gap-3">
                <span className="truncate">
                  <span className="font-medium">{shortAuthor(r.authored_by)}</span>
                  {r.message && (
                    <span className="ml-1.5 text-muted-foreground">— {r.message}</span>
                  )}
                </span>
                <span className="shrink-0 text-xs text-muted-foreground/70">
                  {formatRelativeAsOf(r.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs">
        <span className="text-muted-foreground/70">
          {voice?.declared
            ? `${voice.positiveMarkerCount + voice.antiPatternCount} fingerprint elements declared`
            : 'no voice declaration yet'}
        </span>
        <Link
          href={`/context?path=${encodeURIComponent(VOICE_PATH)}`}
          className="text-muted-foreground/70 hover:text-foreground hover:underline"
        >
          Open _voice.md →
        </Link>
      </div>
    </section>
  );
}
