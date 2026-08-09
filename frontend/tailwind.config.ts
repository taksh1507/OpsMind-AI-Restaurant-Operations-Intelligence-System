import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // "slate" kept as the neutral scale, retoned warm (cast-iron/kitchen) instead of cool blue-gray
        'slate': {
          '50': '#F0E6D2',
          '100': '#E4D7BC',
          '200': '#CBB995',
          '300': '#B8A88C',
          '400': '#9C8A73',
          '500': '#6E5F4C',
          '600': '#4A3F33',
          '700': '#3A322B',
          '800': '#2C2621',
          '900': '#241F1B',
          '950': '#1A1613',
        },
        // "electric" kept as the accent token name for drop-in compatibility, retoned to copper/ember
        'electric': {
          '50': '#FBF0E7',
          '100': '#F5DDC6',
          '200': '#EBBD93',
          '300': '#DE9C64',
          '400': '#D2894B',
          '500': '#C77D3F',
          '600': '#A5652F',
          '700': '#8f5a2c',
          '800': '#6B4522',
          '900': '#4C3119',
          '950': '#2E1D0F',
        },
        'success': '#7A9471',
        'alert': '#C1442E',
      },
      fontFamily: {
        display: ['"Barlow Condensed"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        data: ['"IBM Plex Mono"', 'monospace'],
      },
      backgroundImage: {
        'gradient-ai': 'linear-gradient(135deg, var(--color-slate-900) 0%, var(--color-slate-800) 100%)',
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glow-electric': '0 0 0 1px rgba(199, 125, 63, 0.35)',
        'glow-electric-md': '0 0 0 1px rgba(199, 125, 63, 0.5)',
      },
      borderColor: {
        'electric-glow': 'rgba(199, 125, 63, 0.3)',
      }
    },
  },
  darkMode: 'class',
  plugins: [],
}
export default config
