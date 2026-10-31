/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#142033",
        cream: "#f4efe6",
        card: "#fffdf8",
        line: "#e4d9c8",
        teal: "#0f6e67",
        deep: "#0c3b38",
        gold: "#a67c2d",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 18px 50px rgba(20, 32, 51, 0.08)",
      },
    },
  },
  plugins: [],
};
