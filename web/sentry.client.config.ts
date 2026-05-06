// ADR-250 Phase 1 — Sentry client-side init (browser)
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "production",
  tracesSampleRate: 0.05,  // 5% frontend transactions — free tier headroom
  sendDefaultPii: false,
  // Only initialize when DSN is present (no-op in local dev without it)
  enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
});
