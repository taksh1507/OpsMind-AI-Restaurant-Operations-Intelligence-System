'use client'

import React from 'react'

interface GradientBadgeProps {
  label: string
  type?: 'success' | 'warning' | 'error' | 'info'
}

export function GradientBadge({ label, type = 'info' }: GradientBadgeProps) {
  const typeStyles = {
    success: 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-green-500/30 text-green-300',
    warning: 'bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border-yellow-500/30 text-yellow-300',
    error: 'bg-gradient-to-r from-red-500/20 to-pink-500/20 border-red-500/30 text-red-300',
    info: 'bg-gradient-to-r from-electric-500/20 to-blue-500/20 border-electric-500/30 text-electric-300',
  }

  return (
    <span
      className={`
        inline-block px-3 py-1 rounded-full border text-xs font-semibold
        transition-all duration-200 hover:shadow-lg
        ${typeStyles[type]}
      `}
    >
      {label}
    </span>
  )
}
