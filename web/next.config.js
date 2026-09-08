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
  // ADR-530 D4 — the share link's machine address. A Next dynamic segment
  // cannot carry a literal suffix, so `/s/{token}.txt` (the pasteable form,
  // reachable by adding `.txt` to what is already in someone's clipboard) is
  // expressed as the route `/s/[token]/txt`. An ALIAS of `/s/{token}`, never a
  // second resource — it carries Link: rel="canonical" back to the share URL.
  async rewrites() {
    return [
      { source: '/s/:token.txt', destination: '/s/:token/txt' },
    ];
  },

  async redirects() {
    return [
      { source: '/feed', destination: '/notifications?notifications.pane=understand', permanent: false },
      { source: '/channels', destination: '/chat', permanent: false },
      { source: '/context', destination: '/chat', permanent: false },
      { source: '/home', destination: '/chat', permanent: false },
      // ADR-437 (2026-07-10) — the guided first-boot /setup wizard is deleted
      // (genesis is empty, ADR-414; activation reframes to cold-landing + the
      // shared-artifact wedge). Bookmark-safe transport to the dock anchor.
      { source: '/setup', destination: '/chat', permanent: false },
      // Canon v2 (2026-07-30) — the /freddie marketing page is retired: Freddie
      // is the ambient steward (ADR-454), not a fronted marketing character,
      // and the page sat outside the ratified canon's scope. Bookmark-safe.
      { source: '/freddie', destination: '/', permanent: false },
    ];
  },

  // Vercel Function Storage (2026-09-08). `hideSourceMaps` covers the BROWSER
  // bundle only — `.next/static` carries zero `.map` files. The SERVER bundle
  // was untouched, and 78 of 80 `.nft.json` traces pulled those maps into their
  // function, so every route in the `(authenticated)` group shipped the same
  // maps behind the shared layout's client shell. Measured over the traces at
  // the pre-fix baseline: 2146 MB packed across 77 functions, 1714 MB (80%) of
  // it source maps, largest function 42.3 MB — and the 10 GB free tier held
  // roughly four deployments.
  //
  // The fix has to stop the maps being GENERATED, not delete them afterwards.
  // Next traces each entry's dependencies into `*.nft.json` BEFORE any
  // post-build cleanup hook runs, so a `sourcemaps.filesToDeleteAfterUpload`
  // glob leaves 2797 references to `.js.map` files that no longer exist across
  // 73 manifests. Vercel lstat()s every path it is handed while packing the
  // function and fails the deploy on the first one missing:
  //   ENOENT: no such file or directory, lstat '.next/server/chunks/2511.js.map'
  // `next build` still exits 0 locally, because nothing but Vercel's packing
  // step ever reads a trace — so the traces must be checked directly.
  //
  // Sentry only assigns a devtool when the config leaves one unset
  // (`if (!newConfig.devtool)` in @sentry/nextjs config/webpack.js), picking
  // `source-map` for the server. Our webpack hook runs first (the plugin calls
  // the user's webpack fn at the top of constructWebpackConfigFunction), so a
  // devtool set here wins that check. The CLIENT devtool is untouched, so
  // `hideSourceMaps` still governs browser symbolication — `.next/static`
  // keeps zero `.map` files.
  //
  // The value must be TRUTHY: the guard is `!newConfig.devtool`, so the
  // obvious `false` (webpack's own "no source maps") is falsy and gets
  // overwritten with `source-map`, generating exactly what we are avoiding.
  //
  // Measured over the traces, which is the only thing that reflects what
  // Vercel actually packs:
  //   baseline                       2146 MB packed, 1714 MB maps, 42.3 MB max fn
  //   devtool 'eval'                 1189 MB packed,    0 MB maps, 23.1 MB max fn
  //   hidden-nosources-source-map    1020 MB packed,  561 MB maps, 19.7 MB max fn
  // `eval` emits no separate maps but INLINES them into the JS, so it is
  // bigger overall. `hidden-nosources` keeps the mappings and drops the source
  // text, which is both the smallest and the one that stays symbolicatable.
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.devtool = 'hidden-nosources-source-map';
    }
    return config;
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
