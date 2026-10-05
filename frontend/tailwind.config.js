/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Industrial dark theme palette
        primary: {
          50: '#f0f4ff',
          100: '#e0e9ff',
          200: '#c2d3ff',
          300: '#93b0ff',
          400: '#5c82ff',
          500: '#3355ff',
          600: '#1a33f5',
          700: '#1525e1',
          800: '#1620b5',
          900: '#17208f',
          950: '#111560',
        },
        surface: {
          900: '#0a0d1a',
          800: '#0f1225',
          700: '#151930',
          600: '#1c2240',
          500: '#243050',
          400: '#2e3d65',
        },
        accent: {
          cyan: '#06d6f0',
          green: '#06d690',
          orange: '#f06d06',
          red: '#f03355',
          yellow: '#f0d006',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-glow': 'linear-gradient(135deg, rgba(51,85,255,0.15), rgba(6,214,240,0.05))',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(51,85,255,0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(51,85,255,0.6)' },
        },
      },
      boxShadow: {
        'glow-primary': '0 0 20px rgba(51,85,255,0.3)',
        'glow-cyan': '0 0 20px rgba(6,214,240,0.3)',
        'card': '0 4px 24px rgba(0,0,0,0.4)',
        'card-hover': '0 8px 32px rgba(0,0,0,0.6)',
      },
    },
  },
  plugins: [],
}
