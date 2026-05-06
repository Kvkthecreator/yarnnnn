// ADR-250 Phase 1 — Sentry Next.js plugin wraps the config
const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercel handles SSR natively
};

module.exports = withSentryConfig(nextConfig, {
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
});
