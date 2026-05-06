// ADR-250 Phase 1 — Sentry server-side init (Next.js API routes + SSR)
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.ENVIRONMENT ?? "production",
  tracesSampleRate: 0.1,
  sendDefaultPii: false,
  enabled: !!process.env.SENTRY_DSN,
});
