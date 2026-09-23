// ADR-250 Phase 1 — Sentry Next.js plugin wraps the config
const { withSentryConfig } = require("@sentry/nextjs");

// Bundle analyzer — opt-in via ANALYZE=true (no effect on normal builds).
//   ANALYZE=true npm run build  → opens treemap reports in browser
const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
});

// ADR-660 — next-intl reads its request config (the locale resolution chain +
// the catalogs) from here. No i18n routing: the app carries no locale in its URLs.
const withNextIntl = require("next-intl/plugin")("./i18n/request.ts");

// ADR-661 §8 step 4 — the shell build. `YARNNN_SHELL=1` switches this config to
// a static export of the authenticated app, which is what the packaged desktop
// host serves from disk. The WEB build is untouched when the flag is absent, so
// one config serves both targets (D4: one codebase, N build targets — never a
// fork).
//
// The export drops what only a server can do, and each of those is deliberate:
//   - `rewrites`/`redirects` below warn and do nothing. They are bookmark
//     transport for URLs that exist on the web; a desktop app has no inherited
//     bookmarks (§7.3), so their absence costs nothing.
//   - the six marketing/SEO route handlers and the three legacy dynamic stubs
//     are EXCLUDED from the shell build rather than made static — they belong
//     to the web product (§7.3).
//   - `middleware.ts` does not run. `AuthGate` (§8 step 1) is the gate there,
//     which is why it is mounted unconditionally on both builds.
const SHELL = process.env.YARNNN_SHELL === "1";

// ADR-661 §7m — a shell PRODUCTION build is a distributed binary: every
// `NEXT_PUBLIC_*` origin is frozen into it. A developer's `.env.local` points
// the API at `http://localhost:8000`, and the first signed-in build shipped
// exactly that — the member signed in (Supabase's URL happened to be
// production) and then every API call went to a port on their own machine:
// "Couldn't load your workspaces", an empty desktop. The web build never hit
// this because Vercel supplies its own env. `beforeBuildCommand` pins the API
// origin; this refuses the build if anything still resolves to a loopback or
// plain-http origin, so the mistake cannot reach a DMG. `next dev` is exempt —
// pointing a dev shell at a local API is the point of dev.
//
// §7o — the anon key is frozen the same way, and a build machine with no
// `.env.local` (the Windows CI runner) has none unless it is supplied. Missing,
// the app boots and every Supabase call fails: refuse it here instead.
if (SHELL && process.env.NODE_ENV === "production") {
  if (!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    throw new Error(
      "ADR-661 §7o: the shell build has no NEXT_PUBLIC_SUPABASE_ANON_KEY — the app would boot and fail every Supabase call.",
    );
  }
  const frozen = ["NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_SUPABASE_URL"];
  for (const name of frozen) {
    const value = process.env[name] || "";
    let host = "";
    try {
      host = new URL(value).hostname;
    } catch {}
    const loopback = /^(localhost|127\.|0\.0\.0\.0|\[?::1\]?$)/.test(host);
    if (!value.startsWith("https://") || loopback) {
      throw new Error(
        `ADR-661 §7m: the shell build would freeze ${name}=${value || "(unset)"} into the app. ` +
          "A distributed binary must reach production over https — set it in beforeBuildCommand, not .env.local.",
      );
    }
  }
}

// WHICH ROUTES ARE IN WHICH BUILD, declared rather than moved.
//
// Six marketing/SEO route handlers and three legacy dynamic stubs cannot be
// exported (`force-dynamic`, or a `[param]` with no `generateStaticParams`)
// and must not be: they are the WEB product (§7.3 — a stub exists for bookmark
// continuity, and a desktop app has no inherited bookmarks).
//
// `pageExtensions` is the lever because it is DECLARATIVE: one tree, nothing
// copied or moved per target (D4). Next matches a route file as
// `page.<ext>` / `route.<ext>` EXACTLY, so `route.web.ts` is a route only
// where `web.ts` is a listed extension — the WEB build. The shell build keeps
// Next's default list and therefore cannot see those files at all.
//
// ⚠️ Verified by building, not assumed: the first cut had this backwards
// (giving the SHELL the extra extension), and a `page.web.tsx` probe was
// invisible to BOTH builds — a route silently missing everywhere.
const WEB_ONLY_EXTENSIONS = ["web.tsx", "web.ts"];
const DEFAULT_EXTENSIONS = ["tsx", "ts", "jsx", "js"];

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercel handles SSR natively
  pageExtensions: SHELL
    ? DEFAULT_EXTENSIONS
    : [...WEB_ONLY_EXTENSIONS, ...DEFAULT_EXTENSIONS],
  ...(SHELL
    ? {
        output: "export",
        // The host serves files from disk, so every route needs its own
        // directory + index.html rather than an extensionless file.
        trailingSlash: true,
        // No server means no image optimizer.
        images: { unoptimized: true },
        distDir: ".next-shell",
        // WHICH ROUTES ARE IN THE SHELL, declared rather than moved.
        //
        // Six marketing/SEO route handlers and three legacy dynamic stubs
        // cannot be exported (`force-dynamic`, or a `[param]` with no
        // `generateStaticParams`) and must not be: they are the WEB product
        // (§7.3). A stub exists for bookmark continuity, and a desktop app has
        // no inherited bookmarks.
        //
        // `pageExtensions` is the lever because it is DECLARATIVE — the shell
        // build simply does not see a file named `*.web.tsx` as a route, so
        // the two builds share one tree and nothing is copied, moved or
        // deleted per target (D4). The web build keeps the default list and
        // therefore keeps every route it has today.

      }
    : {}),

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
  //
  // The other factor is deployment COUNT (2026-09-23): the cap was hit again
  // at ~0.7-1 GB per deployment because every push to main deployed, and
  // 329 of the prior 30 days' 555 commits touched neither `web/` nor the
  // `content/` the blog reads (`lib/blog.ts`). `vercel.json`'s ignoreCommand
  // skips those builds; a git error (previous SHA outside the shallow clone)
  // exits 128, which builds, so the rule fails toward deploying.
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.devtool = 'hidden-nosources-source-map';
    }
    return config;
  },
};

module.exports = withBundleAnalyzer(withSentryConfig(withNextIntl(nextConfig), {
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
