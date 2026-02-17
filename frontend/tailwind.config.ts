import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#050810",
        surface: { DEFAULT: "rgba(10,15,26,0.6)", elevated: "#111827" },
        border: { DEFAULT: "rgba(136,146,176,0.15)", strong: "rgba(136,146,176,0.25)", accent: "rgba(255,77,77,0.3)" },
        text: { primary: "#f0f4ff", secondary: "#8892b0", tertiary: "#5a6480", inverse: "#050810" },
        primary: { DEFAULT: "#ff4d4d", hover: "#e63946", active: "#991b1b", muted: "rgba(255,77,77,0.10)" },
        accent: { purple: "#9b6dff", pink: "#e84d8a", orange: "#f5a623", coral: "#ff7e7e" },
        accent2: { bright: "#00e5cc", mid: "#14b8a6", glow: "rgba(0,229,204,0.4)" },
        bull: "#22c55e",
        bear: "#ef4444",
        warning: "#f59e0b",
        info: "#3b82f6",
        sidebar: "rgba(10,15,26,0.95)",
      },
      fontFamily: {
        sans: ["Satoshi", "Inter", "system-ui", "sans-serif"],
        display: ["Clash Display", "Space Grotesk", "system-ui", "sans-serif"],
        mono: ["SF Mono", "Fira Code", "JetBrains Mono", "Menlo", "monospace"],
      },
      boxShadow: {
        sm: "0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2)",
        md: "0 4px 12px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3)",
        lg: "0 10px 24px rgba(0,0,0,0.5), 0 4px 8px rgba(0,0,0,0.3)",
        xl: "0 20px 40px rgba(0,0,0,0.6)",
        card: "0 2px 8px rgba(0,0,0,0.3)",
        "card-hover": "0 8px 24px rgba(0,0,0,0.4), 0 0 20px rgba(255,77,77,0.1)",
        "glow-coral": "0 0 20px rgba(255,77,77,0.3), 0 0 60px rgba(255,77,77,0.1)",
        "glow-cyan": "0 0 20px rgba(0,229,204,0.3), 0 0 60px rgba(0,229,204,0.1)",
      },
      borderRadius: {
        sm: "8px",
        DEFAULT: "12px",
        md: "14px",
        lg: "18px",
        xl: "24px",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        "fade-in-up": "fadeInUp 0.5s ease-out forwards",
        "slide-in-left": "slideInLeft 0.4s ease-out forwards",
        "gradient-shift": "gradientShift 8s ease infinite",
        "stagger-1": "fadeInUp 0.5s ease-out 0.1s forwards",
        "stagger-2": "fadeInUp 0.5s ease-out 0.2s forwards",
        "stagger-3": "fadeInUp 0.5s ease-out 0.3s forwards",
        "stagger-4": "fadeInUp 0.5s ease-out 0.4s forwards",
        "stagger-5": "fadeInUp 0.5s ease-out 0.5s forwards",
        "stagger-6": "fadeInUp 0.5s ease-out 0.6s forwards",
      },
      keyframes: {
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp: { "0%": { opacity: "0", transform: "translateY(8px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        fadeInUp: { "0%": { opacity: "0", transform: "translateY(20px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        slideInLeft: { "0%": { opacity: "0", transform: "translateX(-20px)" }, "100%": { opacity: "1", transform: "translateX(0)" } },
        gradientShift: { "0%, 100%": { backgroundPosition: "0% 50%" }, "50%": { backgroundPosition: "100% 50%" } },
      },
    },
  },
  plugins: [],
};
export default config;
