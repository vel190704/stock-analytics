/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary':   '#0d1117',
        'bg-secondary': '#161b22',
        'bg-card':      '#21262d',
        'border-dark':  '#30363d',
        'green-gain':   '#3fb950',
        'red-loss':     '#f85149',
        'amber-ma':     '#d29922',
        'blue-accent':  '#58a6ff',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['"Inter"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
