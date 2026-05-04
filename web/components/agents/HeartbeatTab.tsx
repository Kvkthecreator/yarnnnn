'use client';

/**
 * HeartbeatTab — YARNNN detail Heartbeat tab.
 *
 * Shows the operational heartbeat per ADR-249 D5: the active recurrences
 * that constitute the Operator ↔ System loop, their cadence, and last/next
 * run timing.
 *
 * Distinct from /schedule (which is a browse surface) and /work (which is
 * output-focused). This tab is a control panel: the operator sees the pulse
 * of the operation and can adjust cadence inline.
 *
 * Inline cadence editing: PUT /api/recurrences/{slug} with { schedule }.
 * YAML declaration is mirrored server-side via ManageRecurrence (ADR-231 +
 * ADR-235). No chat round-trip needed for a simple cadence change.
 */

import { useState, useRef } from 'react';
import { Activity, Check, X, Pause, Play } from 'lucide-react';
import Link from 'next/link';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { humanizeSchedule, cadenceCategory } from '@/lib/schedule';
import { formatRelativeTime } from '@/lib/formatting';
import { WORK_ROUTE } from '@/lib/routes';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { Recurrence } from '@/types';

const SHAPE_LABELS: Record<string, string> = {
  deliverable: 'Report',
  accumulation: 'Tracker',
  action: 'Action',
  maintenance: 'System',
};

function heartbeatSummary(active: Recurrence[]): string {
  if (active.length === 0) return 'No active recurrences';
  const scheduled = active.filter((r) => r.schedule && cadenceCategory(r) === 'recurring');
  const reactive = active.filter((r) => cadenceCategory(r) === 'reactive');
  const parts: string[] = [`${active.length} active`];
  if (scheduled.length) parts.push(`${scheduled.length} scheduled`);
  if (reactive.length) parts.push(`${reactive.length} reactive`);
  return parts.join(' · ');
}

// ─── Inline cadence editor ───────────────────────────────────────────────────

function CadenceCell({
  recurrence,
  onUpdated,
}: {
  recurrence: Recurrence;
  onUpdated: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(recurrence.schedule ?? '');
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const category = cadenceCategory(recurrence);

  const displayLabel =
    category === 'recurring'
      ? humanizeSchedule(recurrence.schedule)
      : category === 'reactive'
        ? 'Reactive'
        : 'On demand';

  const startEdit = () => {
    setValue(recurrence.schedule ?? '');
    setEditing(true);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const cancel = () => setEditing(false);

  const save = async () => {
    if (value === recurrence.schedule) { setEditing(false); return; }
    setSaving(true);
    try {
      await api.recurrences.update(recurrence.slug, { schedule: value || undefined });
      onUpdated();
    } finally {
      setSaving(false);
      setEditing(false);
    }
  };

  if (editing) {
    return (
      <div className="flex items-center gap-1.5">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') cancel(); }}
          placeholder="daily, weekly, 0 8 * * 1-5…"
          className="text-xs rounded border border-border px-1.5 py-0.5 bg-background w-36 focus:outline-none focus:ring-1 focus:ring-foreground/20"
          disabled={saving}
          autoFocus
        />
        <button
          onClick={save}
          disabled={saving}
          className="text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Save"
        >
          <Check className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={cancel}
          className="text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Cancel"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={startEdit}
      className="text-xs text-muted-foreground hover:text-foreground hover:underline underline-offset-2 transition-colors text-left"
      title="Click to edit cadence"
    >
      {displayLabel}
    </button>
  );
}

// ─── Pause / resume toggle ────────────────────────────────────────────────────

function PauseToggle({ recurrence, onUpdated }: { recurrence: Recurrence; onUpdated: () => void }) {
  const [loading, setLoading] = useState(false);
  const isPaused = recurrence.paused === true;

  const toggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setLoading(true);
    try {
      await api.recurrences.update(recurrence.slug, {
        status: isPaused ? 'active' : 'paused',
      });
      onUpdated();
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={toggle}
      disabled={loading}
      className={cn(
        'shrink-0 p-1 rounded transition-colors',
        isPaused
          ? 'text-amber-500 hover:text-foreground'
          : 'text-muted-foreground/40 hover:text-muted-foreground',
      )}
      title={isPaused ? 'Resume' : 'Pause'}
    >
      {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
    </button>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function HeartbeatTab() {
  const { tasks, loading, reload } = useAgentsAndRecurrences();

  // Exclude archived; split active vs paused
  const live = tasks.filter((r) => r.status !== 'archived');
  const active = live.filter((r) => !r.paused);
  const paused = live.filter((r) => r.paused);

  if (loading) {
    return <div className="py-8 text-center text-sm text-muted-foreground">Loading…</div>;
  }

  return (
    <div className="space-y-6">
      {/* Summary line */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Activity className="w-4 h-4 shrink-0" />
        <span>{heartbeatSummary(active)}</span>
      </div>

      {/* Active */}
      {active.length === 0 ? (
        <div className="rounded-lg border border-border/50 px-4 py-6 text-center text-sm text-muted-foreground">
          No active recurrences. Ask YARNNN in chat to set one up.
        </div>
      ) : (
        <div className="rounded-lg border border-border/50 divide-y divide-border/40">
          {active.map((r) => (
            <HeartbeatRow key={r.id} recurrence={r} onUpdated={reload} />
          ))}
        </div>
      )}

      {/* Paused */}
      {paused.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/50">
            Paused
          </p>
          <div className="rounded-lg border border-border/50 divide-y divide-border/40 opacity-60">
            {paused.map((r) => (
              <HeartbeatRow key={r.id} recurrence={r} onUpdated={reload} />
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-muted-foreground/40">
        Click a cadence to edit it. Pause/resume with the icon. Full detail at{' '}
        <Link href="/work" className="underline underline-offset-2 hover:text-muted-foreground">
          Work
        </Link>
        {' '}or{' '}
        <Link href="/schedule" className="underline underline-offset-2 hover:text-muted-foreground">
          Schedule
        </Link>
        .
      </p>
    </div>
  );
}

function HeartbeatRow({
  recurrence,
  onUpdated,
}: {
  recurrence: Recurrence;
  onUpdated: () => void;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 group">
      {/* Title + shape badge — links to /work detail */}
      <Link
        href={`${WORK_ROUTE}?task=${recurrence.slug}`}
        className="flex-1 min-w-0 flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        <span className="text-sm font-medium truncate">{recurrence.title}</span>
        {recurrence.shape && (
          <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
            {SHAPE_LABELS[recurrence.shape] ?? recurrence.shape}
          </span>
        )}
      </Link>

      {/* Inline cadence editor */}
      <CadenceCell recurrence={recurrence} onUpdated={onUpdated} />

      {/* Last / next run */}
      <div className="shrink-0 text-[11px] text-muted-foreground/50 text-right w-20 hidden sm:block">
        {recurrence.next_run_at
          ? `Next ${formatRelativeTime(recurrence.next_run_at)}`
          : recurrence.last_run_at
            ? `Last ${formatRelativeTime(recurrence.last_run_at)}`
            : '—'}
      </div>

      {/* Pause toggle */}
      <PauseToggle recurrence={recurrence} onUpdated={onUpdated} />
    </div>
  );
}
