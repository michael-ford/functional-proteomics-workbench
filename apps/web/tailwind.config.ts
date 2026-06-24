import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "rgb(var(--border) / <alpha-value>)",
        "border-strong": "rgb(var(--border-strong) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        faint: "rgb(var(--faint) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        wash: "rgb(var(--wash) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        "accent-strong": "rgb(var(--accent-strong) / <alpha-value>)",
        "accent-wash": "rgb(var(--accent-wash) / <alpha-value>)",
        secondary: "rgb(var(--secondary) / <alpha-value>)",
        "secondary-strong": "rgb(var(--secondary-strong) / <alpha-value>)",
        lavender: "rgb(var(--lavender) / <alpha-value>)",
        amber: "rgb(var(--amber) / <alpha-value>)",
        coral: "rgb(var(--coral) / <alpha-value>)",
        signal: "rgb(var(--signal) / <alpha-value>)",
        nav: "rgb(var(--nav) / <alpha-value>)",
        "nav-2": "rgb(var(--nav-2) / <alpha-value>)",
        "nav-border": "rgb(var(--nav-border) / <alpha-value>)",
        "nav-ink": "rgb(var(--nav-ink) / <alpha-value>)",
        "nav-muted": "rgb(var(--nav-muted) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
