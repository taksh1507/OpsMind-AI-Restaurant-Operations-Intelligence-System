'use client'

import React from 'react'

interface ChartCardProps {
  title: string
  children: React.ReactNode
  description?: string
}

export function ChartCard({ title, description, children }: ChartCardProps) {
  return (
    <div
      className={`
        relative overflow-hidden rounded-xl p-6
        bg-gradient-to-br from-slate-800/50 to-slate-900/50
        border border-electric-500/30 hover:border-electric-500/60
        transition-all duration-300
        hover:shadow-glow-electric-md
        group backdrop-blur-sm
      `}
    >
      {/* Header */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-slate-50">{title}</h3>
        {description && (
          <p className="text-xs text-slate-400 mt-1">{description}</p>
        )}
      </div>

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>

      {/* Glow effect on hover */}
      <div
        className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-20 transition-opacity duration-300 pointer-events-none"
        style={{
          background: 'radial-gradient(circle at 50% 50%, rgba(14, 165, 233, 0.1) 0%, transparent 70%)',
        }}
      />
    </div>
  )
}
