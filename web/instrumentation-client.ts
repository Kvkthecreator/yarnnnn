// ADR-250 Phase 1 — Sentry client-side init (browser)
// Renamed from sentry.client.config.ts per Next.js 15 / Turbopack requirements.
//
// Performance (2026-06-19): Sentry's browser SDK was ~149KB of the ~157KB
// shared First-Load JS baseline — every page (landing + app) parsed it on the
// critical path before first paint. We now DEFER both the import and init until
// the browser is idle after first paint: the thin shim below stays in the eager
// entry, but the @sentry/nextjs library code splits into its own lazy chunk
// loaded off the critical path. Trade-off (accepted): errors thrown in the
// first idle-tick window after load aren't captured by the SDK. Uncaught errors
// still surface in app/global-error.tsx.
//
// Note: the `onRouterTransitionStart` navigation-instrumentation export is
// intentionally omitted — exporting it would force Sentry to module-eval time
// and defeat the lazy load. We trade router-transition spans (not error
// capture) for the smaller baseline.

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  const initSentry = () => {
    import("@sentry/nextjs")
      .then((Sentry) => {
        Sentry.init({
          dsn,
          environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "production",
          tracesSampleRate: 0.05,
          sendDefaultPii: false,
          enabled: true,
        });
      })
      .catch(() => {
        // Sentry chunk failed to load — non-fatal; the app runs without it.
      });
  };

  // Defer past first paint. requestIdleCallback where available, else a short
  // timeout fallback (Safari < 16, older browsers).
  if (typeof window !== "undefined") {
    if ("requestIdleCallback" in window) {
      (window as Window & {
        requestIdleCallback: (cb: () => void, opts?: { timeout: number }) => void;
      }).requestIdleCallback(initSentry, { timeout: 3000 });
    } else {
      setTimeout(initSentry, 1500);
    }
  }
}
