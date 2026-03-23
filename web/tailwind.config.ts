import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    // Agent identity colors (web/lib/agent-identity.ts) — must survive purge
    // Avatar backgrounds
    'bg-purple-600', 'bg-blue-500', 'bg-amber-500', 'bg-green-500',
    'bg-teal-500', 'bg-indigo-500', 'bg-rose-500', 'bg-gray-500',
    // Role badge colors
    {
      pattern: /^(bg|text)-(purple|blue|amber|green|teal|indigo|rose)-(100|300|700|900)$/,
      variants: ['dark'],
    },
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
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;