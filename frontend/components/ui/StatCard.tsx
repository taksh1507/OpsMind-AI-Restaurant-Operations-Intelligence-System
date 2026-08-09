'use client'

import React from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  change?: number
  icon?: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  description?: string
}

export function StatCard({
  title,
  value,
  change = 0,
  icon,
  trend = 'neutral',
  description
}: StatCardProps) {
  const isPositive = change > 0
  const isNegative = change < 0

  return (
    <div
      className="
        ticket-perf relative rounded-[3px] p-5
        bg-slate-900 border border-slate-700
        transition-all duration-150 ease-out
        hover:border-electric-700 hover:-translate-y-0.5
      "
    >
      {/* Content */}
      <div className="relative z-10 flex flex-col h-full">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <p className="font-display text-[13px] font-semibold uppercase tracking-wider text-slate-300">
            {title}
          </p>

          {/* Icon chip */}
          {icon && (
            <div
              className="
                w-8 h-8 rounded-[3px] flex items-center justify-center
                bg-slate-800 border border-slate-700
                text-electric-500
              "
            >
              {icon}
            </div>
          )}
        </div>

        <h3 className="font-data text-[28px] font-semibold text-slate-50 leading-none">
          {value}
        </h3>

        {/* Footer with stamp badge */}
        {change !== 0 && (
          <div className="flex items-center gap-2 mt-3.5 pt-3 border-t border-slate-700">
            <span className={`stamp ${isPositive ? 'stamp-up' : isNegative ? 'stamp-down' : ''}`}>
              {isPositive && <TrendingUp size={12} />}
              {isNegative && <TrendingDown size={12} />}
              {isPositive && '+'}
              {change}%
            </span>
            {description && (
              <span className="text-xs text-slate-400">{description}</span>
            )}
          </div>
        )}

        {description && !change && (
          <p className="text-xs text-slate-400 mt-3.5 pt-3 border-t border-slate-700">{description}</p>
        )}
      </div>
    </div>
  )
}
