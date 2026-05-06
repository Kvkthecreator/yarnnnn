// ADR-250 Phase 1 — Sentry edge runtime init (middleware)
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.ENVIRONMENT ?? "production",
  tracesSampleRate: 0.05,
  sendDefaultPii: false,
  enabled: !!process.env.SENTRY_DSN,
});
