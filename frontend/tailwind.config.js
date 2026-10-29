/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#2b2620',
          dark: '#171310',
        },
        paper: {
          DEFAULT: '#f0e3c8',
          light: '#fbf4e4',
          dark: '#e2d0ad',
        },
        tomato: {
          DEFAULT: '#bf3f2c',
          dark: '#8d2a1d',
        },
        mustard: {
          DEFAULT: '#d49a2a',
          dark: '#855915',
        },
        moss: {
          DEFAULT: '#3f6b4f',
          dark: '#284735',
        },
      },
      fontFamily: {
        display: ['Georgia', 'Cambria', '"Times New Roman"', 'serif'],
        mono: ['"Courier New"', 'Courier', 'monospace'],
      },
      boxShadow: {
        journal: '7px 7px 0 rgba(43, 38, 32, 0.22)',
      },
    },
  },
  plugins: [],
};
