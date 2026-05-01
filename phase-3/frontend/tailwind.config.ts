import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#4F46E5",
          hover: "#4338CA",
        },
        risk: {
          lowBg: "#D1FAE5",
          lowText: "#065F46",
          lowBorder: "#6EE7B7",
          uncertainBg: "#FEF3C7",
          uncertainText: "#92400E",
          uncertainBorder: "#FCD34D",
          highBg: "#FEE2E2",
          highText: "#991B1B",
          highBorder: "#FCA5A5",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;
