/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class', // <--- YOU MUST ADD THIS LINE
  content: [
    './core/templates/**/*.html',
    './**/*.html'
  ],
  theme: {
    extend: {
      colors: {
        theme: {
          page: 'var(--bg-page)',
          card: 'var(--bg-card)',
          secondary: 'var(--bg-secondary)',
          main: 'var(--text-main)',
          muted: 'var(--text-muted)',
          accent: 'var(--accent)',
          'hero-start': 'var(--hero-start)', 
          'hero-end': 'var(--hero-end)'      
        }
      }
    }
  },
  plugins: [],
}