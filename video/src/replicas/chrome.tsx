/**
 * chrome.tsx — the product's own design tokens + window chrome, ported into
 * Remotion.
 *
 * WHY THIS FILE EXISTS: the landing-page replicas (web/components/landing/
 * product/*) get their tokens from globals.css, which the marketing pages
 * share with the authenticated app — that shared stylesheet is what keeps a
 * replica from drifting off the product's palette. Remotion has no globals.css,
 * so the tokens are resolved here ONCE, from app/globals.css :root, and every
 * replica reads them from here. Same discipline, different runtime.
 *
 * Values below are the HSL triples at web/app/globals.css:43-49, resolved.
 */

import React from "react";

/** Product tokens — resolved from web/app/globals.css :root (light). */
export const UI = {
  background: "hsl(0, 0%, 100%)",
  foreground: "hsl(240, 10%, 3.9%)",
  muted: "hsl(240, 4.8%, 95.9%)",
  mutedForeground: "hsl(240, 3.8%, 46.1%)",
  border: "hsl(240, 5.9%, 90%)",
  primary: "hsl(240, 5.9%, 10%)",
  /** Attribution accent dots — Tailwind 500-weights, as the replicas use. */
  blue: "#3b82f6",
  amber: "#fbbf24",
  teal: "#14b8a6",
  amberBg: "rgba(255, 251, 235, 0.4)",
  amberBorder: "#fde68a",
  amberText: "#b45309",
  blueBg: "#eff6ff",
  blueBorder: "#bfdbfe",
  blueText: "#1d4ed8",
};

/** A translucent foreground, matching the replicas' text-foreground/80 etc. */
export const fg = (alpha: number) => `hsla(240, 10%, 3.9%, ${alpha})`;
/** A translucent muted-foreground, matching text-muted-foreground/70 etc. */
export const mutedFg = (alpha: number) => `hsla(240, 3.8%, 46.1%, ${alpha})`;
/** A translucent border, matching border-border/50 etc. */
export const borderAlpha = (alpha: number) => `hsla(240, 5.9%, 90%, ${alpha})`;

/**
 * ProductWindow — the OS window chrome, ported from
 * web/components/landing/product/ProductWindow.tsx (itself a replica of the
 * shipped components/shell/WindowFrame.tsx, ADR-297 D14/D19.1).
 *
 * Faithful: rounded border + shadow, 32px title bar on muted/30 carrying the
 * macOS traffic-light cluster (12px circles, #ff5f57 / #febc2e / #28c840) and
 * a centered text-xs title. Scaled up for video legibility via `scale`.
 */
export const ProductWindow: React.FC<{
  title: string;
  width: number;
  children: React.ReactNode;
  /** Multiplies every dimension — the replicas are authored at browser scale. */
  scale?: number;
}> = ({ title, width, children, scale = 1 }) => (
  <div
    style={{
      width,
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      borderRadius: 8 * scale,
      border: `${Math.max(1, scale)}px solid ${UI.border}`,
      backgroundColor: UI.background,
      boxShadow: `0 ${10 * scale}px ${30 * scale}px rgba(0,0,0,0.10)`,
    }}
  >
    <div
      style={{
        position: "relative",
        display: "flex",
        height: 32 * scale,
        flexShrink: 0,
        alignItems: "center",
        borderBottom: `${Math.max(1, scale)}px solid ${UI.border}`,
        backgroundColor: "hsla(240, 4.8%, 95.9%, 0.3)",
        paddingLeft: 12 * scale,
        paddingRight: 12 * scale,
      }}
    >
      <div style={{ display: "flex", flexShrink: 0, gap: 6 * scale }}>
        {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
          <span
            key={c}
            style={{
              height: 12 * scale,
              width: 12 * scale,
              borderRadius: "50%",
              backgroundColor: c,
            }}
          />
        ))}
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          fontSize: 12 * scale,
          fontWeight: 500,
          color: fg(0.8),
        }}
      >
        {title}
      </div>
    </div>
    <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>{children}</div>
  </div>
);
