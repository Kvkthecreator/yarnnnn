/**
 * Shared design system for all yarnnn video compositions.
 *
 * Brand assets live in video/public/ — copied from web/public/.
 * Fonts: Pacifico (brand wordmark), Inter (body).
 * Colors: peach bg, black text, orange accent (yarn ball).
 */

import React from "react";
import { Img, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";
import { loadFont as loadGoogleFont } from "@remotion/google-fonts/Inter";
import { loadFont as loadLocalFont } from "@remotion/fonts";

// ── Fonts ──────────────────────────────────────────────
const { fontFamily: interFamily } = loadGoogleFont("normal", {
  weights: ["400", "700", "900"],
  subsets: ["latin"],
});

// Pacifico loaded from local file (same TTF as web/public/fonts/)
loadLocalFont({
  family: "Pacifico",
  url: staticFile("Pacifico-Regular.ttf"),
  weight: "400",
});

export const FONT = {
  brand: "'Pacifico', cursive",
  body: `'${interFamily}', system-ui, sans-serif`,
};

// ── Colors (from marketing ads + landing page) ─────────
export const COLOR = {
  /** Peach background — exact match to ad frames */
  bg: "#fce8d5",
  /** Near-black foreground */
  fg: "#1a1a1a",
  /** Muted text */
  muted: "rgba(26, 26, 26, 0.45)",
  /** Orange accent (yarn ball) */
  orange: "#e8622c",
  /** Platform colors */
  slack: "#E01E5A",
  gmail: "#EA4335",
  notion: "#000000",
  calendar: "#4285F4",
  /** Status */
  green: "#16a34a",
};

// ── Animation helpers ──────────────────────────────────
export const useFadeIn = (delay = 0, duration = 15) => {
  const frame = useCurrentFrame();
  return interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });
};

export const useSlideUp = (delay = 0, distance = 40) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame, fps, delay, config: { damping: 200 } });
  return interpolate(p, [0, 1], [distance, 0]);
};

export const useSpring = (delay = 0, config = { damping: 200 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame, fps, delay, config });
};

// ── Reusable atoms ─────────────────────────────────────

/** Yarn ball logo from circleonly_yarnnn.png */
export const YarnBall: React.FC<{ size?: number }> = ({ size = 56 }) => (
  <Img src={staticFile("circleonly_yarnnn.png")} width={size} height={size} />
);

/** "yarnnn.com" watermark — bottom-right, Pacifico italic-ish */
export const Watermark: React.FC<{ opacity?: number }> = ({ opacity = 1 }) => (
  <div
    style={{
      position: "absolute",
      bottom: 48,
      right: 56,
      fontFamily: FONT.brand,
      fontSize: 36,
      color: COLOR.fg,
      opacity,
    }}
  >
    yarnnn.com
  </div>
);

/** Platform icon SVGs — exact paths from IntegrationHub.tsx */
const PLATFORM_SVGS: Record<string, string> = {
  Slack: "M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z",
  Gmail: "M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z",
  Notion: "M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z",
  Calendar: "M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11zM9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm-8 4H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2z",
};

export const PlatformSVG: React.FC<{
  name: string;
  color: string;
  size?: number;
  iconSize?: number;
}> = ({ name, color, size = 80, iconSize = 28 }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.22,
      backgroundColor: color,
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      boxShadow: `0 6px 24px ${color}44`,
    }}
  >
    <svg viewBox="0 0 24 24" width={iconSize} height={iconSize} fill="white">
      <path d={PLATFORM_SVGS[name] || ""} />
    </svg>
  </div>
);
