/**
 * CTA targets — single source of truth for marketing-surface call-to-action hrefs.
 *
 * Per SITE-COPY-SPEC-v1 §0.7 + discourse §-9.7: CTA hrefs route through these
 * constants, never scattered string literals, so the two pending swaps have one home.
 *
 * CHECKOUT GUARD (spec §0.8): the active pricing model is the ADR-172/291 balance
 * gate (pay-as-you-go) — the `/pricing` page reflects this. ADR-334's seat tiers were
 * DEMOTED 2026-06-19 to a deferred hypothesis (evidence-gated; see ADR-334 Amendment
 * 2026-06-19), so there is no seat checkout to wire and none is on the roadmap. All
 * marketing CTAs route to `signup` (the live bare-workspace entry). `seatCheckout`
 * stays null. No CTA may imply a seat purchase.
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
