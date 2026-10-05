import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        radar: { ink: "#17202a", line: "#d8dee7", panel: "#f7f9fb", accent: "#2563eb" }
      }
    }
  },
  plugins: []
} satisfies Config;
