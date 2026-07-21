/**
 * CTA targets — single source of truth for marketing-surface call-to-action hrefs.
 *
 * Per SITE-COPY-SPEC-v1 §0.7 + discourse §-9.7: CTA hrefs route through these
 * constants, never scattered string literals, so the two pending swaps have one home.
 *
 * CHECKOUT GUARD (spec §0.8): the active pricing model is **ADR-445** — TWO axes,
 * seats + a pooled meter, over ADR-396's balance mechanics. The paid subscription IS
 * the per-additional-human seat price (seat 1 free); there is no separate base fee.
 * The `/pricing` page reflects this.
 *
 * The guard that still holds: plan checkout is an IN-APP action (the
 * SubscriptionCard's tier + top-up flow via `/api/subscription`), NOT a marketing
 * CTA — marketing surfaces route to `signup` and never open a checkout. That is why
 * `seatCheckout` stays null.
 *
 * The guard that DIED with ADR-445: this block used to read "a plan subscription is
 * not a seat" and "no CTA may imply a seat purchase". Both are now FALSE — under
 * ADR-445 the plan subscription is literally the seat price, and the pricing page,
 * landing, and FAQ all correctly sell a seat. Do not restore that wording; following
 * it would revert the Phase-3 coherence pass.
 *
 * Still true, and a different claim: **ADR-334's** per-seat *autonomy* pricing (trust
 * as the price axis) stays retired (ADR-445 §10). An ADR-445 seat is human ACCESS,
 * never an autonomy tier.
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
   * Seat-checkout URL from a MARKETING surface. NULL by design, and it stays null
   * even though ADR-445 seats are live: seat checkout is an in-app action (the
   * SubscriptionCard), so no marketing CTA opens a checkout. This is a surface
   * boundary, not a statement about the pricing model.
   */
  seatCheckout: null as string | null,
} as const;

/** Default primary-CTA label until the Stage-B swap (spec §0.6). */
export const PRIMARY_CTA_LABEL = "Start free";
