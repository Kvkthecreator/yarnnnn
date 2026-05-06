'use client';

/**
 * ReviewerCadencePanel — Reviewer heartbeat cadence display (ADR-251 D5).
 *
 * Renders below AUTONOMY.md in the Reviewer's Autonomy tab. Shows:
 *   - reflection schedule (cron string from back-office.yaml, humanised)
 *   - calibration schedule
 *   - last run timestamp + verdict for reflection
 *   - last run timestamp for calibration
 *
 * Data source: GET /api/agents/reviewer/cadence (live aggregate — not a
 * file render). L3 structured affordance per ADR-245 three-layer model.
 * Content class: live_aggregate (read-only, system-owned — no write path).
 *
 * Edit is chat-routed: "Edit cadence via chat →" seeds a YARNNN message.
 */

import { useEffect, useState } from 'react';
import { Clock, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useTP } from '@/contexts/TPContext';

interface CadenceData {
  reflection: {
    schedule: string | null;
    last_ran_at: string | null;
    last_verdict: string | null;
  };
  calibration: {
    schedule: string | null;
    last_ran_at: string | null;
  };
}

function humaniseCron(cron: string | null): string {
  if (!cron) return '—';
  // Common patterns from back-office.yaml
  const m = cron.match(/^(\d+)\s+(\d+)\s+\*\s+\*\s+\*$/);
  if (m) {
    const h = parseInt(m[2], 10);
    const min = parseInt(m[1], 10);
    const hh = h.toString().padStart(2, '0');
    const mm = min.toString().padStart(2, '0');
    return `daily ${hh}:${mm} UTC`;
  }
  return cron;
}

function relativeTime(iso: string | null): string {
  if (!iso) return 'never';
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const diffH = Math.floor(diffMs / 3_600_000);
  if (diffH < 1) return 'less than 1h ago';
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.floor(diffH / 24);
  return `${diffD}d ago`;
}

export function ReviewerCadencePanel() {
  const { sendMessage } = useTP();
  const [data, setData] = useState<CadenceData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.agents.reviewerCadence()
      .then(d => setData(d))
      .catch(() => {}) // non-fatal — panel stays hidden
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (!data) return null;

  const noData =
    !data.reflection.schedule &&
    !data.calibration.schedule &&
    !data.reflection.last_ran_at &&
    !data.calibration.last_ran_at;

  if (noData) return null;

  return (
    <div className="mt-4 rounded-lg border border-border/60 bg-muted/20 px-4 py-3 space-y-3">
      <div className="flex items-center gap-2">
        <Clock className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Reviewer cadence
        </span>
      </div>

      <div className="space-y-2">
        {/* Reflection */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium">Reflection</p>
            <p className="text-xs text-muted-foreground">
              {humaniseCron(data.reflection.schedule)}
              {data.reflection.last_ran_at && (
                <> · last ran {relativeTime(data.reflection.last_ran_at)}</>
              )}
              {data.reflection.last_verdict && (
                <span className="ml-1 text-muted-foreground/70">
                  ({data.reflection.last_verdict})
                </span>
              )}
            </p>
          </div>
          <RefreshCw className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground/40" />
        </div>

        {/* Calibration */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium">Calibration</p>
            <p className="text-xs text-muted-foreground">
              {humaniseCron(data.calibration.schedule)}
              {data.calibration.last_ran_at && (
                <> · last ran {relativeTime(data.calibration.last_ran_at)}</>
              )}
            </p>
          </div>
          <RefreshCw className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground/40" />
        </div>
      </div>

      <button
        onClick={() =>
          sendMessage(
            `I want to change how often my Reviewer reflects — currently set to ${humaniseCron(data.reflection.schedule)}. Walk me through the options.`
          )
        }
        className="text-xs text-primary hover:text-primary/80 transition-colors"
      >
        Edit cadence via chat →
      </button>
    </div>
  );
}
