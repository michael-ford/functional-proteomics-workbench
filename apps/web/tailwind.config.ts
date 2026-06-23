import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "rgb(var(--border) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        wash: "rgb(var(--wash) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        signal: "rgb(var(--signal) / <alpha-value>)",
      },
    },
  },
  plugins: [],
};

export default config;
