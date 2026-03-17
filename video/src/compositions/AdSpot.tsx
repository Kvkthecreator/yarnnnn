/**
 * AdSpot — punchy social ad (6-10s).
 *
 * Matches the existing Frame 2-6 ad style:
 *   - Peach background
 *   - Bold black Inter 900 text, centered
 *   - Yarn ball as visual divider
 *   - "yarnnn.com" watermark bottom-right in Pacifico
 *
 * Each variant is a standalone composition so you can render
 * them independently: `npx remotion render src/index.ts Ad_WorksWhileYouSleep out/ad-sleep.mp4`
 */

import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import { COLOR, FONT, YarnBall, Watermark, useSpring } from "../design";

// ── Core ad frame layout ───────────────────────────────
const AdFrame: React.FC<{
  topLines: string[];
  bottomLines: string[];
}> = ({ topLines, bottomLines }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Top text slams in
  const topScale = useSpring(0, { damping: 15, stiffness: 120 });
  const topOpacity = interpolate(topScale, [0, 1], [0, 1]);

  // Yarn ball pops
  const ballScale = useSpring(Math.round(0.6 * fps), { damping: 12, stiffness: 100 });

  // Bottom text slides up
  const bottomDelay = Math.round(1.0 * fps);
  const bottomProgress = interpolate(
    frame,
    [bottomDelay, bottomDelay + Math.round(0.4 * fps)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.quad) }
  );
  const bottomY = interpolate(bottomProgress, [0, 1], [60, 0]);

  // Watermark fade
  const wmOpacity = interpolate(
    frame,
    [bottomDelay + Math.round(0.3 * fps), bottomDelay + Math.round(0.6 * fps)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLOR.bg,
        justifyContent: "center",
        alignItems: "center",
        padding: 80,
      }}
    >
      {/* Top headline */}
      <div
        style={{
          opacity: topOpacity,
          transform: `scale(${topScale})`,
          textAlign: "center",
          marginBottom: 48,
        }}
      >
        {topLines.map((line, i) => (
          <div
            key={i}
            style={{
              fontFamily: FONT.body,
              fontSize: 96,
              fontWeight: 900,
              color: COLOR.fg,
              lineHeight: 1.1,
              letterSpacing: "-0.03em",
            }}
          >
            {line}
          </div>
        ))}
      </div>

      {/* Yarn ball divider */}
      <div style={{ transform: `scale(${ballScale})`, marginBottom: 48 }}>
        <YarnBall size={64} />
      </div>

      {/* Bottom headline */}
      <div
        style={{
          opacity: bottomProgress,
          transform: `translateY(${bottomY}px)`,
          textAlign: "center",
        }}
      >
        {bottomLines.map((line, i) => (
          <div
            key={i}
            style={{
              fontFamily: FONT.body,
              fontSize: 96,
              fontWeight: 900,
              color: COLOR.fg,
              lineHeight: 1.1,
              letterSpacing: "-0.03em",
            }}
          >
            {line}
          </div>
        ))}
      </div>

      <Watermark opacity={wmOpacity} />
    </AbsoluteFill>
  );
};

// ── Ad variants (matching existing Frame assets + new ones) ──

export const Ad_WorksWhileYouSleep: React.FC = () => (
  <AdFrame topLines={["AI Agents"]} bottomLines={["works while", "you sleep"]} />
);

export const Ad_FirstAIEmployee: React.FC = () => (
  <AdFrame topLines={["your first", "AI employee"]} bottomLines={["starts", "Monday"]} />
);

export const Ad_DontGetCaught: React.FC = () => (
  <AdFrame topLines={["don\u2019t get", "caught"]} bottomLines={["using", "yarnnn.com"]} />
);

export const Ad_ReplaceChatGPT: React.FC = () => (
  <AdFrame topLines={["AI Agents"]} bottomLines={["that replace", "chatGPT"]} />
);

export const Ad_StillUsingChatGPT: React.FC = () => (
  <AdFrame topLines={["still using", "ChatGPT?"]} bottomLines={["AI Agents", "4 Dummies"]} />
);

// New variants
export const Ad_ConnectOnce: React.FC = () => (
  <AdFrame topLines={["connect once"]} bottomLines={["supervise", "from there"]} />
);

export const Ad_ContextCompounds: React.FC = () => (
  <AdFrame topLines={["context", "compounds"]} bottomLines={["every cycle", "gets better"]} />
);

export const Ad_StopRebuilding: React.FC = () => (
  <AdFrame topLines={["stop", "rebuilding", "context"]} bottomLines={["let AI", "remember"]} />
);
