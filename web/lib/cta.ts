/**
 * CTA targets — single source of truth for marketing-surface call-to-action hrefs.
 *
 * Per SITE-COPY-SPEC-v1 §0.7 + discourse §-9.7: CTA hrefs route through these
 * constants, never scattered string literals, so the two pending swaps have one home.
 *
 * CHECKOUT GUARD (spec §0.8): ADR-334 is Ratified-direction; the seat-checkout
 * substrate (P1 entitlement record, P2 LS seat products + webhooks, P3 tier plumbing)
 * does NOT exist. `seatCheckout` stays null until ADR-334 P2 ships. All marketing CTAs
 * — including the `/pricing` seat cards — route to `signup` (the live bare-workspace
 * entry) under "seat trials open soon" framing. No CTA may imply a working seat purchase.
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
   * ADR-334 seat-checkout URL. NULL until P2 (LS seat products + webhooks) ships.
   * Until then, seat-card CTAs route to `signup`. Do not wire a checkout URL here
   * without the entitlement substrate behind it (spec §0.8).
   */
  seatCheckout: null as string | null,
} as const;

/** Default primary-CTA label until the Stage-B swap (spec §0.6). */
export const PRIMARY_CTA_LABEL = "Start free";
