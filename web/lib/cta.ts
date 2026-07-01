/**
 * CTA targets — single source of truth for marketing-surface call-to-action hrefs.
 *
 * Per SITE-COPY-SPEC-v1 §0.7 + discourse §-9.7: CTA hrefs route through these
 * constants, never scattered string literals, so the two pending swaps have one home.
 *
 * CHECKOUT GUARD (spec §0.8): the active pricing model is ADR-396 — a Type-B
 * subscription (Free / Starter / Pro) over the metered balance; the `/pricing` page
 * reflects this. Plan checkout is an IN-APP action (the SubscriptionCard's tier +
 * top-up flow via `/api/subscription`), NOT a marketing CTA — so marketing surfaces
 * still route to `signup` (the live bare-workspace entry) and never open a checkout.
 * The ADR-396 tiers are plans, NOT ADR-334 seats: ADR-334's per-seat autonomy pricing
 * stays DEMOTED to a Rung-2/Phase-2 hypothesis, so `seatCheckout` stays null and no CTA
 * may imply a seat purchase. (A plan subscription is not a seat.)
 *
 * STAGE-B SWAP (spec §0.6): when ADR-331 Stage B ships the retrospective audit, the
 * primary CTA label upgrades from "Start free" to `stageBLabel`. The slot is wired now,
 * unused until then.
 */
export const CTA = {
  /** Live bare-workspace entry. There is no separate signup route — login IS the entry. */
  signup: "/auth/login",
  /** Secondary sitewide CTA target. */
  howItWorks: "/how-it-works",
  /** Pricing page (for cross-page "See pricing" links). */
  pricing: "/pricing",
  /** ADR-331 Stage-B primary-CTA label swap. Wired, unused until Stage B ships. */
  stageBLabel: "Bring your track record",
  /**
   * ADR-334 seat-checkout URL. NULL — ADR-334 is a deferred hypothesis (demoted
   * 2026-06-19), not a roadmap item. Do not wire a checkout URL here unless the seat
   * model clears its unblock conditions and ships entitlement substrate (spec §0.8).
   */
  seatCheckout: null as string | null,
} as const;

/** Default primary-CTA label until the Stage-B swap (spec §0.6). */
export const PRIMARY_CTA_LABEL = "Start free";
