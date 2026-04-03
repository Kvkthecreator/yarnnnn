import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme, FONT_SIZES, resolveColor } from "../theme";

type Props = {
  text: string;
  size?: string;
  color?: string;
  delay?: number;
};

export const TextElement: React.FC<Props> = ({
  text,
  size = "md",
  color,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();

  const opacity = interpolate(frame - delay, [0, fps * 0.3], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <div
      style={{
        opacity,
        fontSize: FONT_SIZES[size] || FONT_SIZES.md,
        fontWeight: 400,
        color: resolveColor(color, theme),
        lineHeight: 1.5,
      }}
    >
      {text}
    </div>
  );
};
