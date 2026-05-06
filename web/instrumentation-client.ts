// ADR-250 Phase 1 — Sentry client-side init (browser)
// Renamed from sentry.client.config.ts per Next.js 15 / Turbopack requirements.
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "production",
  tracesSampleRate: 0.05,
  sendDefaultPii: false,
  enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
});
