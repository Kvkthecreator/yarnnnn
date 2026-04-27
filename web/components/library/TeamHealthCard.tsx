'use client';

/**
 * TeamHealthCard — Cockpit pane #5 in the six-question cockpit framing
 * (2026-04-28 reshape). The pane that answers "is the team itself
 * healthy?"
 *
 * Universal across delegation products. Reads three diagnostic signals
 * from existing endpoints (no new API):
 *   1. Active agent count (workforce alive)
 *   2. Active task count (work routed to that workforce)
 *   3. Pending proposal count (decisions in flight — too many or too few
 *      both signal calibration drift)
 *
 * The operator usually doesn't read this every visit; it's there when
 * something feels off. Click-through navigates to /agents for diagnosis.
 *
 * Replaces the prior IntelligenceCard pane (which was a daily-synthesis
 * artifact rendered via maintain-overview output). The synthesis-shaped
 * "what does the team think" pane is preserved as a separate concern —
 * if/when needed, the bundle can register a `WorkspaceSynthesis`
 * component pointing at the maintain-overview output. Cockpit-default
 * is the diagnostic, not the synthesis.
 */

import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api/client';

interface HealthSignals {
  agentCount: number;
  taskCount: number;
  proposalCount: number;
}

export function TeamHealthCard() {
  const [signals, setSignals] = useState<HealthSignals | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [agentsR, tasksR, proposalsR] = await Promise.allSettled([
        api.agents.list('active'),
        api.tasks.list(),
        api.proposals.list('pending', 50),
      ]);
      if (cancelled) return;
      const agents = agentsR.status === 'fulfilled' ? agentsR.value : [];
      const tasks = tasksR.status === 'fulfilled' ? tasksR.value : [];
      const proposals = proposalsR.status === 'fulfilled' ? proposalsR.value.proposals : [];
      const activeTasks = tasks.filter((t) => t.status === 'active').length;
      setSignals({
        agentCount: agents.length,
        taskCount: activeTasks,
        proposalCount: proposals.length,
      });
    })();
    return () => { cancelled = true; };
  }, []);

  if (!signals) return null;

  const empty = signals.agentCount === 0 && signals.taskCount === 0 && signals.proposalCount === 0;

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
        <Activity className="h-3.5 w-3.5" />
        Team health
      </div>
      {empty ? (
        <p className="text-xs text-muted-foreground">
          No active workforce yet. Agents materialize as you author tasks in chat.
        </p>
      ) : (
        <div className="grid grid-cols-3 gap-4 text-sm">
          <Signal
            href="/agents"
            label="Workforce"
            value={`${signals.agentCount}`}
            unit={signals.agentCount === 1 ? 'agent' : 'agents'}
          />
          <Signal
            href="/work"
            label="Active work"
            value={`${signals.taskCount}`}
            unit={signals.taskCount === 1 ? 'task' : 'tasks'}
          />
          <Signal
            href="/agents?agent=reviewer"
            label="In review"
            value={`${signals.proposalCount}`}
            unit={signals.proposalCount === 1 ? 'proposal' : 'proposals'}
          />
        </div>
      )}
    </section>
  );
}

function Signal({
  href, label, value, unit,
}: {
  href: string;
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <Link href={href} className="block hover:opacity-80">
      <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
        {label}
      </div>
      <div className="mt-0.5 flex items-baseline gap-1">
        <span className="text-lg font-semibold text-foreground">{value}</span>
        <span className="text-[11px] text-muted-foreground">{unit}</span>
      </div>
    </Link>
  );
}
