import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "../theme";

type Props = {
  delay?: number;
};

export const Divider: React.FC<Props> = ({ delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();

  const width = interpolate(frame - delay, [0, fps * 0.4], [0, 100], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <div
      style={{
        width: `${width}%`,
        height: 2,
        backgroundColor: theme.muted,
        opacity: 0.3,
        margin: "16px 0",
      }}
    />
  );
};
