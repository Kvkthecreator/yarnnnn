/**
 * SocialClip — 15s vertical (1080×1920) clip for Reels/TikTok/Shorts.
 *
 * Quick-hit format:
 *   1. Hook text (3s)
 *   2. Platform icons fly in (3s)
 *   3. "Agents run while you sleep" (3s)
 *   4. "yarnnn.com" CTA (3s)
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
import { COLOR, FONT, YarnBall, PlatformSVG, useSpring } from "../design";

const SceneHook: React.FC = () => {
  const scale = useSpring(0, { damping: 15, stiffness: 120 });

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center", padding: 60 }}>
      <div style={{ transform: `scale(${scale})`, textAlign: "center" }}>
        <div style={{ fontFamily: FONT.body, fontSize: 72, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          still copying
        </div>
        <div style={{ fontFamily: FONT.body, fontSize: 72, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          into ChatGPT?
        </div>
      </div>
    </AbsoluteFill>
  );
};

const ScenePlatforms: React.FC = () => {
  const { fps } = useVideoConfig();
  const platforms = [
    { name: "Slack", color: COLOR.slack, delay: 0 },
    { name: "Gmail", color: COLOR.gmail, delay: Math.round(0.2 * fps) },
    { name: "Notion", color: COLOR.notion, delay: Math.round(0.4 * fps) },
    { name: "Calendar", color: COLOR.calendar, delay: Math.round(0.6 * fps) },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 32, alignItems: "center" }}>
        <div style={{ fontFamily: FONT.body, fontSize: 36, fontWeight: 400, color: COLOR.muted, marginBottom: 16 }}>
          connect your tools
        </div>
        <div style={{ display: "flex", gap: 32 }}>
          {platforms.map(({ name, color, delay }) => {
            const s = useSpring(delay, { damping: 12, stiffness: 120 });
            return (
              <div key={name} style={{ transform: `scale(${s})` }}>
                <PlatformSVG name={name} color={color} size={88} iconSize={32} />
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const SceneAgents: React.FC = () => {
  const scale = useSpring(0, { damping: 15, stiffness: 120 });
  const ballScale = useSpring(15, { damping: 12 });

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center", padding: 60 }}>
      <div style={{ transform: `scale(${scale})`, textAlign: "center", marginBottom: 32 }}>
        <div style={{ fontFamily: FONT.body, fontSize: 64, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          AI agents
        </div>
        <div style={{ fontFamily: FONT.body, fontSize: 64, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          run while
        </div>
        <div style={{ fontFamily: FONT.body, fontSize: 64, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          you sleep
        </div>
      </div>
      <div style={{ transform: `scale(${ballScale})` }}>
        <YarnBall size={56} />
      </div>
    </AbsoluteFill>
  );
};

const SceneCTA: React.FC = () => {
  const logoScale = useSpring(0, { damping: 12 });
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const urlOpacity = interpolate(frame, [15, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `scale(${logoScale})`, marginBottom: 24 }}>
        <YarnBall size={80} />
      </div>
      <div style={{ fontFamily: FONT.brand, fontSize: 72, color: COLOR.fg, transform: `scale(${logoScale})` }}>
        yarnnn
      </div>
      <div style={{ opacity: urlOpacity, fontFamily: FONT.body, fontSize: 28, color: COLOR.muted, marginTop: 20 }}>
        yarnnn.com
      </div>
    </AbsoluteFill>
  );
};

export const SocialClip: React.FC = () => {
  const { fps } = useVideoConfig();
  const scenes = [
    { seconds: 3, Component: SceneHook },
    { seconds: 3, Component: ScenePlatforms },
    { seconds: 3, Component: SceneAgents },
    { seconds: 3, Component: SceneCTA },
  ];

  let offset = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg }}>
      {scenes.map(({ seconds, Component }, i) => {
        const from = offset;
        const dur = seconds * fps;
        offset += dur;
        return (
          <Sequence key={i} from={from} durationInFrames={dur} premountFor={fps}>
            <Component />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
