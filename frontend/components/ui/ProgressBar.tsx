'use client'

import React from 'react'

interface ProgressBarProps {
  label: string
  value: number
  max?: number
  color?: 'electric' | 'success' | 'warning' | 'error'
  showPercentage?: boolean
}

export function ProgressBar({
  label,
  value,
  max = 100,
  color = 'electric',
  showPercentage = true,
}: ProgressBarProps) {
  const percentage = (value / max) * 100

  const colorClasses = {
    electric: 'bg-accent',
    success: 'bg-success',
    warning: 'bg-warning',
    error: 'bg-alert',
  }

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-sm text-foreground">{label}</label>
        {showPercentage && (
          <span className="font-data text-sm font-semibold text-foreground">{percentage.toFixed(0)}%</span>
        )}
      </div>
      <div className="relative w-full h-1.5 bg-surface rounded-full overflow-hidden border border-line">
        <div
          className={`h-full ${colorClasses[color]} transition-all duration-500 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
