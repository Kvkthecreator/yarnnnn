"use client";

/**
 * SeatPanel — what this workspace is charged for its people, and the one act
 * that changes it (2026-07-22).
 *
 * WHY THIS EXISTS. The Billing card's "Manage seats" button used to open the
 * Members roster — an access-management surface with no price on it — from a
 * button sitting inside a billing card. The operator read it as "take me to the
 * payment screen for seats" and landed on permissions. This is that payment
 * screen.
 *
 * THE MODEL IT RENDERS (ADR-445 Axis ①). Entrance is paid: every human beyond
 * the owner is $20/mo. But the count is DERIVED from the roster
 * (`billable_seats = max(0, humans − included_seats)`), never stored as a
 * purchased quantity — no migration has a seat-count column, and the webhook
 * treats an LS/roster mismatch as `seat_quantity_drift` to RECORD, not truth to
 * honor. So the roster is authoritative and LS's quantity is its mirror.
 *
 * The consequence for this UI: there is no seat SPINNER, because a spinner
 * would have nothing to write — set it to 15, invite nobody, and the next
 * reconcile computes 1. The invite IS the purchase. So the buy action here is
 * "Invite a teammate", priced inline (+$20/mo) so the operator sees the charge
 * they are agreeing to at the moment they agree to it. Removing a person is
 * likewise the refund action, and lives on the roster where the person does.
 *
 * ON SHOWING DOLLARS. ADR-396's transparency contract hides "a running dollar
 * meter" — the CONSUMPTION figure — so the operator reasons in allowance, not
 * cost. It does not hide PRICES: the top-up chips have always shown $20/$50,
 * and the pricing page shows tier prices. A seat fee is a price (a fixed,
 * predictable, pre-agreed monthly amount), not a meter reading, so it is shown.
 * `seat_fee_usd` has been computed and returned by /subscription/status all
 * along and rendered NOWHERE — this is the first surface to show the operator
 * what their team actually costs.
 */

import { useState } from "react";
import { Loader2, UserRoundPlus, X } from "lucide-react";
import { useWorkspaceMembers } from "@/lib/workspace/viewer";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import type { SubscriptionStatus } from "@/types";

// Roles that occupy a paid seat. AI principals (foreign-llm / a2a / own-agent /
// platform) are NEVER seats and never charged — the same HUMAN_SEAT_ROLES split
// the backend counts by (billing_tiers.count_human_seats).
const HUMAN_ROLES = new Set(["owner", "member"]);

function money(n: number): string {
  return n % 1 === 0 ? `$${n}` : `$${n.toFixed(2)}`;
}

export function SeatPanel({
  status,
  seatPriceUsd,
  onClose,
}: {
  status: SubscriptionStatus | null;
  /** The per-additional-human price, derived from the tier (never hardcoded). */
  seatPriceUsd: number;
  onClose: () => void;
}) {
  const { members } = useWorkspaceMembers();
  const { navigateToSurface } = useSurfacePreferences();
  const [busy, setBusy] = useState(false);

  const exempt = status?.billing_exempt ?? false;
  const includedSeats = status?.included_seats ?? 1;
  const billable = status?.billable_seats ?? 0;
  const seatTotal = status?.seat_fee_usd ?? 0;

  // The humans, owner first — the order that makes "seat 1 is included" legible.
  const humans = members
    .filter((m) => HUMAN_ROLES.has(m.role) && m.status === "active")
    .sort((a, b) => (a.role === "owner" ? -1 : b.role === "owner" ? 1 : 0));

  // Which rows are the INCLUDED ones (the billing baseline) vs the billed ones.
  // Derived by position so it always matches the backend's arithmetic rather
  // than restating it: the first `included_seats` humans are covered.
  const rowPrice = (i: number) =>
    exempt ? "comped" : i < includedSeats ? "included" : `${money(seatPriceUsd)}/mo`;

  const goToRoster = () => {
    setBusy(true);
    navigateToSurface("workspace-settings", { pane: "members" });
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-medium">Seats on this workspace</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {humans.length} {humans.length === 1 ? "person" : "people"}
            {!exempt && billable > 0 && ` · ${billable} billed`}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close seats panel"
          className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* The people, each with what they cost. This is the whole point of the
          panel: a seat charge attributable to a NAME, not an opaque total. */}
      <div className="rounded-lg border border-border divide-y divide-border/60">
        {humans.length === 0 ? (
          <div className="px-3 py-3 text-sm text-muted-foreground">
            <Loader2 className="mr-2 inline h-3.5 w-3.5 animate-spin" />
            Loading the roster…
          </div>
        ) : (
          humans.map((m, i) => (
            <div key={m.principal_id} className="flex items-center justify-between gap-3 px-3 py-2.5">
              <div className="min-w-0">
                <div className="truncate text-sm">{m.label ?? "A member"}</div>
                <div className="text-[11px] capitalize text-muted-foreground">{m.role}</div>
              </div>
              <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                {rowPrice(i)}
              </span>
            </div>
          ))
        )}

        {/* The total, on the same rule as the rows it sums. */}
        {!exempt && humans.length > 0 && (
          <div className="flex items-center justify-between gap-3 bg-muted/40 px-3 py-2.5">
            <span className="text-sm font-medium">Seat total</span>
            <span className="text-sm font-medium tabular-nums">{money(seatTotal)}/mo</span>
          </div>
        )}
      </div>

      {/* The BUY action. Priced inline: the operator sees the charge at the
          moment they agree to it, not on next month's invoice. It routes to the
          roster because that is where the invite is authored — the purchase and
          the grant are one act (there is no seat to buy separately). */}
      <button
        type="button"
        onClick={goToRoster}
        disabled={busy}
        className="flex w-full items-center justify-between gap-3 rounded-lg border border-border px-3 py-2.5 text-left transition-colors hover:bg-muted/40 disabled:opacity-60"
      >
        <span className="flex items-center gap-2.5">
          <UserRoundPlus className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Invite a teammate</span>
        </span>
        <span className="shrink-0 text-xs text-muted-foreground">
          {exempt ? "comped" : `+${money(seatPriceUsd)}/mo`}
        </span>
      </button>

      <p className="text-xs leading-relaxed text-muted-foreground">
        {exempt
          ? "This workspace is comped — people are free to add, and no seat charge applies."
          : `Seat ${includedSeats === 1 ? "1 (you) is" : `1–${includedSeats} are`} included. ` +
            "Each additional person is a billed seat, charged from your next renewal; " +
            "removing someone stops their seat at the same boundary. "}
        AI connections are always free and never count as seats.
      </p>
    </div>
  );
}
