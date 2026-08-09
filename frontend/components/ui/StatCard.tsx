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
        bg-surface border border-line
        transition-all duration-150 ease-out
        hover:border-accent hover:-translate-y-0.5
      "
    >
      {/* Content */}
      <div className="relative z-10 flex flex-col h-full">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <p className="font-display text-[13px] font-semibold uppercase tracking-wider text-cream-dim">
            {title}
          </p>

          {/* Icon chip */}
          {icon && (
            <div
              className="
                w-8 h-8 rounded-[3px] flex items-center justify-center
                bg-surface-2 border border-line
                text-accent
              "
            >
              {icon}
            </div>
          )}
        </div>

        <h3 className="font-data text-[28px] font-semibold text-foreground leading-none">
          {value}
        </h3>

        {/* Footer with stamp badge */}
        {change !== 0 && (
          <div className="flex items-center gap-2 mt-3.5 pt-3 border-t border-line">
            <span className={`stamp ${isPositive ? 'stamp-up' : isNegative ? 'stamp-down' : ''}`}>
              {isPositive && <TrendingUp size={12} />}
              {isNegative && <TrendingDown size={12} />}
              {isPositive && '+'}
              {change}%
            </span>
            {description && (
              <span className="text-xs text-cream-dim">{description}</span>
            )}
          </div>
        )}

        {description && !change && (
          <p className="text-xs text-cream-dim mt-3.5 pt-3 border-t border-line">{description}</p>
        )}
      </div>
    </div>
  )
}
