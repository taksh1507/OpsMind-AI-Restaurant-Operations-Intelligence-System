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
      className={`
        relative overflow-hidden rounded-xl p-6
        bg-gradient-to-br from-slate-800/50 to-slate-900/50
        border border-electric-500/30 hover:border-electric-500/60
        transition-all duration-300 ease-out
        hover:shadow-glow-electric-md hover:from-slate-800/70 hover:to-slate-900/70
        group backdrop-blur-sm
        before:absolute before:inset-0 before:bg-gradient-to-br before:from-electric-500/0 before:to-electric-600/0
        before:opacity-0 hover:before:opacity-10 before:transition-opacity before:duration-300
      `}
    >
      {/* Background glow effect */}
      <div
        className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-30 transition-opacity duration-300"
        style={{
          background: 'radial-gradient(circle at 50% 50%, rgba(14, 165, 233, 0.1) 0%, transparent 70%)',
        }}
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col h-full">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-sm font-medium text-slate-400 mb-2">{title}</p>
            <h3 className="text-3xl md:text-4xl font-bold text-slate-50">
              {value}
            </h3>
          </div>

          {/* Icon */}
          {icon && (
            <div
              className={`
                p-3 rounded-lg
                bg-gradient-to-br from-electric-500/20 to-electric-600/20
                border border-electric-500/30
                text-electric-400
                group-hover:from-electric-500/30 group-hover:to-electric-600/30
                group-hover:text-electric-300 transition-all duration-300
              `}
            >
              {icon}
            </div>
          )}
        </div>

        {/* Footer with change percentage */}
        {change !== 0 && (
          <div className="flex items-center gap-2 mt-auto pt-4 border-t border-electric-500/10">
            <div
              className={`
                flex items-center gap-1 px-2 py-1 rounded-md
                ${
                  isPositive
                    ? 'bg-green-500/20 text-green-400'
                    : isNegative
                      ? 'bg-red-500/20 text-red-400'
                      : 'bg-slate-700/30 text-slate-400'
                }
              `}
            >
              {isPositive && <TrendingUp size={16} />}
              {isNegative && <TrendingDown size={16} />}
              <span className="text-sm font-semibold">
                {isPositive && '+'}
                {change}%
              </span>
            </div>
            {description && (
              <span className="text-xs text-slate-500">{description}</span>
            )}
          </div>
        )}

        {description && !change && (
          <p className="text-xs text-slate-500 mt-4">{description}</p>
        )}
      </div>

      {/* Top border accent glow */}
      <div
        className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-electric-500/50 to-transparent opacity-0
        group-hover:opacity-100 transition-opacity duration-300"
      />
    </div>
  )
}
