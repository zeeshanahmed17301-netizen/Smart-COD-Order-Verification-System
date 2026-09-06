/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#0f766e', // Teal-700
          hover: '#115e59',   // Teal-800
          dark: '#0f4f48',    // Muted deep teal
        },
        blue: {
          50: '#e6f4f1',
          100: '#cde9e3',
          200: '#9dd3c7',
          300: '#6dbdac',
          400: '#43a192',
          500: '#2d8c7d',
          600: '#1f7768',
          700: '#0f6457',
          800: '#0c5046',
          900: '#0a423b',
          950: '#062d29',
        },
        background: '#F8FAFC', // Slate-50
        surface: '#FFFFFF',
      }
    },
  },
  plugins: [],
}
