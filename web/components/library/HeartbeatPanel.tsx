'use client';

/**
 * HeartbeatPanel — generic library component for any heartbeating agent.
 *
 * Renders the periodic-trigger (heartbeat) state for a single agent. Reads
 * back-office.yaml entries prefixed `back-office-{agent_slug}-*` plus
 * execution_events for last-run data via GET /api/agents/{slug}/heartbeats.
 *
 * Library-grade per ADR-225 §library scoping: heartbeats are a generic
 * Trigger sub-shape (FOUNDATIONS Axiom 4 — periodic pulse), not a Reviewer
 * concern. Reviewer is the first consumer; any future agent with declared
 * periodic triggers renders through this same component.
 *
 * L3 structured affordance per ADR-245 three-layer model. Content class:
 * live_aggregate (read-only, system-owned — no write path). Mutation flows
 * through chat (operator asks YARNNN to edit cadence).
 *
 * Hides itself when the agent has no declared heartbeats (zero triggers).
 */

import { useEffect, useState } from 'react';
import { Clock, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useNarrative } from '@/contexts/NarrativeContext';

interface HeartbeatTrigger {
  slug: string;
  display_name: string;
  schedule: string | null;
  paused: boolean;
  last_ran_at: string | null;
  last_outcome: string | null;
}

interface HeartbeatPanelProps {
  agentSlug: string;
  /** Optional friendly name used in the chat-edit prompt seed. Defaults to "this agent". */
  agentLabel?: string;
}

function humaniseCron(cron: string | null): string {
  if (!cron) return '—';
  // "M H * * *" → daily HH:MM UTC
  const daily = cron.match(/^(\d+)\s+(\d+)\s+\*\s+\*\s+\*$/);
  if (daily) {
    const hh = daily[2].padStart(2, '0');
    const mm = daily[1].padStart(2, '0');
    return `daily ${hh}:${mm} UTC`;
  }
  // "M H * * 1-5" → weekdays HH:MM UTC
  const weekdays = cron.match(/^(\d+)\s+(\d+)\s+\*\s+\*\s+1-5$/);
  if (weekdays) {
    const hh = weekdays[2].padStart(2, '0');
    const mm = weekdays[1].padStart(2, '0');
    return `weekdays ${hh}:${mm} UTC`;
  }
  return cron;
}

function relativeTime(iso: string | null): string {
  if (!iso) return 'never';
  const diffH = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000);
  if (diffH < 1) return 'less than 1h ago';
  if (diffH < 24) return `${diffH}h ago`;
  return `${Math.floor(diffH / 24)}d ago`;
}

/**
 * Strip a leading display-name prefix from the outcome summary so the verdict
 * reads cleanly. "Reflection stand_down" → "stand_down". Falls back to raw
 * summary on no match.
 */
function formatOutcome(outcome: string | null, displayName: string): string | null {
  if (!outcome) return null;
  // Match the common "{Word} {verdict}" shape from the reflection writer
  const firstWord = displayName.split(/\s+/).slice(-1)[0];
  if (firstWord && outcome.startsWith(`${firstWord} `)) {
    return outcome.slice(firstWord.length + 1).trim();
  }
  return outcome;
}

export function HeartbeatPanel({ agentSlug, agentLabel }: HeartbeatPanelProps) {
  const { sendMessage } = useNarrative();
  const [triggers, setTriggers] = useState<HeartbeatTrigger[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.agents.heartbeats(agentSlug)
      .then((d) => { if (!cancelled) setTriggers(d.triggers || []); })
      .catch(() => { if (!cancelled) setTriggers([]); });
    return () => { cancelled = true; };
  }, [agentSlug]);

  if (triggers === null) return null;       // loading
  if (triggers.length === 0) return null;   // agent has no heartbeats

  const label = agentLabel || 'this agent';
  const editPrompt = `I want to change how often ${label} heartbeats — walk me through the current cadence and the options.`;

  return (
    <div className="rounded-lg border border-border/60 bg-muted/20 px-4 py-3 space-y-3">
      <div className="flex items-center gap-2">
        <Clock className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Heartbeats
        </span>
      </div>

      <div className="space-y-2">
        {triggers.map((t) => {
          const outcome = formatOutcome(t.last_outcome, t.display_name);
          return (
            <div key={t.slug} className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-medium">
                  {t.display_name}
                  {t.paused && (
                    <span className="ml-2 rounded bg-muted px-1 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                      paused
                    </span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">
                  {humaniseCron(t.schedule)}
                  {t.last_ran_at && (
                    <> · last ran {relativeTime(t.last_ran_at)}</>
                  )}
                  {outcome && (
                    <span className="ml-1 text-muted-foreground/70">
                      ({outcome})
                    </span>
                  )}
                </p>
              </div>
              <RefreshCw className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground/40" />
            </div>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() => sendMessage(editPrompt)}
        className="text-xs text-primary hover:text-primary/80 transition-colors"
      >
        Edit cadence via chat →
      </button>
    </div>
  );
}
