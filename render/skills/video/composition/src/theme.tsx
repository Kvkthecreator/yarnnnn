import React, { createContext, useContext } from "react";
import type { Theme } from "./types";

const DEFAULT_THEME: Theme = {
  background: "#0f172a",
  foreground: "#ffffff",
  accent: "#3b82f6",
  muted: "#94a3b8",
};

const ThemeContext = createContext<Theme>(DEFAULT_THEME);

export const ThemeProvider: React.FC<{
  theme: Partial<Theme>;
  children: React.ReactNode;
}> = ({ theme, children }) => {
  const merged = { ...DEFAULT_THEME, ...theme };
  return (
    <ThemeContext.Provider value={merged}>{children}</ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);

// Font size map
export const FONT_SIZES: Record<string, number> = {
  sm: 20,
  md: 28,
  lg: 36,
  xl: 48,
  "2xl": 64,
  "3xl": 96,
};

// Badge colors
export const BADGE_COLORS: Record<string, string> = {
  green: "#22c55e",
  red: "#ef4444",
  yellow: "#eab308",
  blue: "#3b82f6",
};

export const resolveColor = (
  color: string | undefined,
  theme: Theme
): string => {
  if (!color || color === "foreground") return theme.foreground;
  if (color === "muted") return theme.muted;
  if (color === "accent") return theme.accent;
  return color; // pass-through hex values
};
