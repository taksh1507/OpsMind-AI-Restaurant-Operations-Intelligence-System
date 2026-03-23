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
    electric: 'from-electric-500 to-electric-400',
    success: 'from-green-500 to-emerald-400',
    warning: 'from-yellow-500 to-orange-400',
    error: 'from-red-500 to-pink-400',
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-slate-300">{label}</label>
        {showPercentage && (
          <span className="text-sm font-semibold text-electric-300">{percentage.toFixed(0)}%</span>
        )}
      </div>
      <div className="relative w-full h-2 bg-slate-900/50 rounded-full overflow-hidden border border-slate-800">
        <div
          className={`h-full bg-gradient-to-r ${colorClasses[color]} transition-all duration-500 ease-out`}
          style={{ width: `${percentage}%` }}
        />
        <div
          className={`absolute inset-0 bg-gradient-to-r ${colorClasses[color]} opacity-50 blur-sm`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
