import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        brand: ["'Pacifico'", "cursive"],
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        border: "hsl(var(--border))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        // Overlay + interactive surface tokens (shadcn-standard, added
        // 2026-07-03 / ADR-400 polish). These map the CSS vars defined in
        // globals.css so `bg-popover`, `hover:bg-accent`, `text-destructive`,
        // `bg-card`, `text-success` resolve app-wide. Nested `.DEFAULT`/
        // `.foreground` lets `bg-popover` + `text-popover-foreground` both work.
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
      },
    },
  },
  // tailwindcss-animate (2026-07-03): the shadcn-ecosystem companion to the
  // token set above. 5 components under components/tp/ already assumed its
  // `animate-in fade-in slide-in-from-*` classes but the plugin was never
  // installed — the entrances were silently dead. Installing it is the singular
  // path: it revives those, backs the feedback-layer entrances (replacing the
  // three hand-rolled keyframes in globals.css), and means any shadcn component
  // copied in animates correctly by default. ~3KB, purge-friendly, zero runtime.
  plugins: [require("@tailwindcss/typography"), require("tailwindcss-animate")],
};

export default config;