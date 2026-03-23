import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'slate': {
          '50': '#f9fafb',
          '100': '#f3f4f6',
          '200': '#e5e7eb',
          '300': '#d1d5db',
          '400': '#9ca3af',
          '500': '#6b7280',
          '600': '#4b5563',
          '700': '#374151',
          '800': '#1f2937',
          '900': '#111827',
          '950': '#030712',
        },
        'electric': {
          '50': '#f0f9ff',
          '100': '#e0f2fe',
          '200': '#bae6fd',
          '300': '#7dd3fc',
          '400': '#38bdf8',
          '500': '#0ea5e9',
          '600': '#0284c7',
          '700': '#0369a1',
          '800': '#075985',
          '900': '#0c3d66',
          '950': '#08223f',
        }
      },
      backgroundImage: {
        'gradient-ai': 'linear-gradient(135deg, var(--color-slate-900) 0%, var(--color-slate-800) 100%)',
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glow-electric': '0 0 20px rgba(14, 165, 233, 0.5)',
        'glow-electric-md': '0 0 30px rgba(14, 165, 233, 0.6)',
      },
      borderColor: {
        'electric-glow': 'rgba(14, 165, 233, 0.3)',
      }
    },
  },
  darkMode: 'class',
  plugins: [],
}
export default config
