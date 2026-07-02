// ADR-250 Phase 1 — Sentry Next.js plugin wraps the config
const { withSentryConfig } = require("@sentry/nextjs");

// Bundle analyzer — opt-in via ANALYZE=true (no effect on normal builds).
//   ANALYZE=true npm run build  → opens treemap reports in browser
const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercel handles SSR natively

  // ADR-385 follow-on (2026-06-30) — bookmark-safety for the retired legacy
  // surface URLs. The `feed` (ADR-370) + `context` (ADR-385) surface slugs
  // folded/renamed into `channels`; the alias surface entries were deleted
  // (full alias deletion), so the prior `/feed` + `/context` page-component
  // redirect stubs are removed. These server redirects preserve external
  // bookmarks. Next.js carries the original query string through by default,
  // so `?prompt=…` deep-links survive.
  //   `/feed` was always the NARRATIVE alias. The 2026-07-02 ACTIVITY re-scope
  //   retired the Channels Flow pane (a Channels surface tracks only boundary
  //   crossings, not the global narrative), so `/feed` now lands on the
  //   narrative's real home — Notifications → Activity (`understand` pane).
  //   `/context` lands on Channels (default: the In crossing-ledger).
  async redirects() {
    return [
      { source: '/feed', destination: '/notifications?notifications.pane=understand', permanent: false },
      { source: '/context', destination: '/channels', permanent: false },
    ];
  },
};

module.exports = withBundleAnalyzer(withSentryConfig(nextConfig, {
  // Sentry webpack plugin options
  silent: true,           // suppress build output noise
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  // Only upload source maps when SENTRY_AUTH_TOKEN is set (CI/Vercel)
  // Local dev builds skip this cleanly
  authToken: process.env.SENTRY_AUTH_TOKEN,
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
  // ADR-250: Sentry init is now handled via instrumentation.ts (Next.js 15 API).
  // Disable auto-instrumentation of middleware to prevent edge runtime crashes
  // when the old sentry.edge.config.ts no longer exists.
  autoInstrumentMiddleware: false,
  autoInstrumentServerFunctions: false,
}));
