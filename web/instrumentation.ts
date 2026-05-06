// ADR-250 Phase 1 — Next.js instrumentation file (server + edge Sentry init)
// Replaces sentry.server.config.ts and sentry.edge.config.ts per Next.js 15
// instrumentation API. Both runtimes call register() on startup.

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { default: Sentry } = await import("@sentry/nextjs");
    Sentry.init({
      dsn: process.env.SENTRY_DSN,
      environment: process.env.ENVIRONMENT ?? "production",
      tracesSampleRate: 0.1,
      sendDefaultPii: false,
      enabled: !!process.env.SENTRY_DSN,
    });
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    const { default: Sentry } = await import("@sentry/nextjs");
    Sentry.init({
      dsn: process.env.SENTRY_DSN,
      environment: process.env.ENVIRONMENT ?? "production",
      tracesSampleRate: 0.05,
      sendDefaultPii: false,
      enabled: !!process.env.SENTRY_DSN,
    });
  }
}
