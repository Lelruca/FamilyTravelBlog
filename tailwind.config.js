const defaultTheme = require("tailwindcss/defaultTheme");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./layouts/**/*.html",
    "./content/**/*.md",
    "./assets/js/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", ...defaultTheme.fontFamily.sans],
        serif: ["Lora", ...defaultTheme.fontFamily.serif],
      },
      // Expose --accent as a Tailwind color token (runtime CSS variable)
      colors: {
        accent: "var(--accent)",
      },
      typography: ({ theme }) => ({
        travel: {
          css: {
            "--tw-prose-body": theme("colors.neutral[800]"),
            "--tw-prose-headings": "var(--accent)",
            "--tw-prose-links": "var(--accent)",
            "--tw-prose-bold": theme("colors.neutral[900]"),
            a: {
              textDecorationColor: "var(--accent)",
            },
          },
        },
      }),
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
