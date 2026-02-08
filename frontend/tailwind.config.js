/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e3f2fd',
          100: '#bbdefb',
          200: '#90caf9',
          300: '#64b5f6',
          400: '#42a5f5',
          500: '#2196f3',
          600: '#1e88e5',
          700: '#1976d2',
          800: '#1565c0',
          900: '#0d47a1',
        },
        success: {
          50: '#e8f5e9',
          500: '#4caf50',
          600: '#43a047',
        },
        error: {
          50: '#ffebee',
          500: '#f44336',
          600: '#e53935',
        },
        warning: {
          50: '#fff3e0',
          500: '#ff9800',
          600: '#fb8c00',
        },
      },
    },
  },
  plugins: [],
};
