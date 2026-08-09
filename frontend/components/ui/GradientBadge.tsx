'use client'

import React from 'react'

interface GradientBadgeProps {
  label: string
  type?: 'success' | 'warning' | 'error' | 'info'
}

export function GradientBadge({ label, type = 'info' }: GradientBadgeProps) {
  const typeStyles = {
    success: 'bg-success/10 border-success/30 text-success',
    warning: 'bg-warning/10 border-warning/30 text-warning',
    error: 'bg-alert/10 border-alert/30 text-alert',
    info: 'bg-accent/10 border-accent/30 text-accent',
  }

  return (
    <span
      className={`
        inline-block px-3 py-1 rounded-[3px] border text-xs font-display font-semibold tracking-wide
        transition-colors hover:border-opacity-60
        ${typeStyles[type]}
      `}
    >
      {label}
    </span>
  )
}
