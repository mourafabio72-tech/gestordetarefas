/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Padrão Sage & Creme (Zoaria/BPS4)
        white: '#fffdf9',           // "branco" dos cards vira creme quente
        primary: {                  // acento verde-oliva
          50: '#eef1ea',
          100: '#dbe3d4',
          200: '#c3cfb9',
          300: '#a7b89a',
          400: '#86977a',
          500: '#6e7f63',
          600: '#5f7057',
          700: '#566450',
          800: '#45503f',
          900: '#333c2f',
        },
        gray: {                     // "cinza" vira sage/creme quente
          50: '#faf7f0',
          100: '#ede2d1',
          200: '#dccdb6',
          300: '#cbb99b',
          400: '#a99e88',
          500: '#808a74',
          600: '#55614e',
          700: '#3f4a3c',
          800: '#2f3b2f',
          900: '#232c22',
        },
      },
    },
  },
  plugins: [],
}
