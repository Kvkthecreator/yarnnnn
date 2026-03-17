import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

export const YarnnnIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, from: 0, to: 1, durationInFrames: 30 });
  const taglineOpacity = interpolate(frame, [40, 60], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#faf8f5",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          transform: `scale(${logoScale})`,
          fontFamily: "system-ui, sans-serif",
          fontSize: 120,
          fontWeight: 400,
          color: "#1a1a1a",
          letterSpacing: "-0.02em",
        }}
      >
        yarnnn
      </div>
      <div
        style={{
          opacity: taglineOpacity,
          fontFamily: "system-ui, sans-serif",
          fontSize: 32,
          color: "rgba(26, 26, 26, 0.5)",
          marginTop: 24,
        }}
      >
        Autonomous AI that already knows your work.
      </div>
    </AbsoluteFill>
  );
};
