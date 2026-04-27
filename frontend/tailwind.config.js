/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201d",
        slate: "#56625d",
        mist: "#f4f7f5",
        line: "#dfe7e2",
        teal: "#0f766e",
        amber: "#b7791f"
      },
      boxShadow: {
        soft: "0 18px 45px rgba(23, 32, 29, 0.08)"
      }
    }
  },
  plugins: []
};
