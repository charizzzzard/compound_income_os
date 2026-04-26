/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: 'var(--paper-50)',
        ink: 'var(--ink-900)',
        graphite: 'var(--accent-600)',
        gold: 'var(--gold-500)',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
        serif: ['var(--font-serif)'],
      },
      boxShadow: {
        calm: 'var(--shadow-md)',
        deep: 'var(--shadow-lg)',
      },
    },
  },
  plugins: [],
}
