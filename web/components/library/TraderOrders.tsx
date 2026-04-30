'use client';

/**
 * TraderOrders — program section component for alpha-trader (order: 4).
 *
 * ADR-243 Phase C. Renders the recent orders table matching the Alpaca
 * brokerage dashboard aesthetic per COCKPIT-COMPONENT-DESIGN.md.
 *
 * Data: api.cockpit.recentOrders() → /api/cockpit/recent-orders
 *
 * Graceful degradation: empty state when Alpaca unreachable or no orders.
 */

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type Order = {
  id: string;
  symbol: string;
  side: string;
  qty: string;
  filled_qty: string;
  type: string;
  time_in_force: string;
  limit_price?: string | null;
  filled_avg_price?: string | null;
  status: string;
  created_at: string;
  filled_at?: string | null;
};

function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const diffMs = Date.now() - d.getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

const STATUS_COLOR: Record<string, string> = {
  filled: 'text-emerald-600',
  partially_filled: 'text-amber-600',
  canceled: 'text-muted-foreground',
  expired: 'text-muted-foreground',
  rejected: 'text-destructive',
  pending_new: 'text-blue-600',
  new: 'text-blue-600',
};

export function TraderOrders() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [noConnection, setNoConnection] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.cockpit.recentOrders(10);
        if (cancelled) return;
        if (!res.live && res.fallback_reason === 'no_platform_connection') {
          setNoConnection(true);
        } else {
          setOrders(res.orders);
        }
      } catch {
        if (!cancelled) setOrders([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <section className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }

  if (noConnection) return null; // TraderPortfolio already surfaces the not-connected state

  return (
    <section className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Recent Orders
        </h3>
        <a
          href="/context?path=%2Fworkspace%2Fcontext%2Ftrading%2F"
          className="text-[11px] text-muted-foreground/60 underline-offset-4 hover:text-foreground hover:underline"
        >
          View all →
        </a>
      </div>

      {!orders || orders.length === 0 ? (
        <p className="text-sm text-muted-foreground py-3 text-center">
          No orders. Place a trade via the API or Alpaca dashboard.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                <th className="pb-2 text-left">Asset</th>
                <th className="pb-2 text-left">Type</th>
                <th className="pb-2 text-left">Side</th>
                <th className="pb-2 text-right tabular-nums">Qty</th>
                <th className="pb-2 text-right tabular-nums">Avg. Fill</th>
                <th className="pb-2 text-left">Status</th>
                <th className="pb-2 text-right">Submitted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {orders.map((o) => (
                <tr key={o.id} className="hover:bg-muted/20 transition-colors">
                  <td className="py-1.5 font-mono font-medium">{o.symbol}</td>
                  <td className="py-1.5 text-muted-foreground capitalize">{o.type.replace(/_/g, ' ')}</td>
                  <td className={cn('py-1.5 font-medium capitalize', o.side === 'buy' ? 'text-emerald-600' : 'text-destructive')}>
                    {o.side}
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                    {o.filled_qty || o.qty}
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                    {o.filled_avg_price ? `$${parseFloat(o.filled_avg_price).toFixed(2)}` : '—'}
                  </td>
                  <td className={cn('py-1.5 capitalize', STATUS_COLOR[o.status] ?? 'text-muted-foreground')}>
                    {o.status.replace(/_/g, ' ')}
                  </td>
                  <td className="py-1.5 text-right text-muted-foreground/60">
                    {formatRelative(o.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
