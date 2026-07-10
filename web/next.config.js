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

  // Bookmark-safety for retired legacy surface URLs. Lineage: `feed` (ADR-370)
  // → folded into `context` → renamed `channels` (ADR-385) → DISSOLVED
  // (ADR-415). Next.js carries the original query string through by default, so
  // `?prompt=…`/`?pane=…` deep-links survive.
  //   `/feed` was always the NARRATIVE alias → Notifications → Activity.
  //   `/channels` + `/context` — the Channels surface dissolved (ADR-415).
  //   `/home` — the Home surface was DELETED (ADR-435, the one composition in a
  //   registry of mirrors). All three land on `/chat`, the new dock anchor +
  //   the steward's operating surface; the specific concerns (queue, activity,
  //   files) are reachable by name.
  async redirects() {
    return [
      { source: '/feed', destination: '/notifications?notifications.pane=understand', permanent: false },
      { source: '/channels', destination: '/chat', permanent: false },
      { source: '/context', destination: '/chat', permanent: false },
      { source: '/home', destination: '/chat', permanent: false },
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
