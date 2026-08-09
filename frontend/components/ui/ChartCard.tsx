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
        ticket-perf relative overflow-hidden rounded-[3px] p-6
        bg-surface border border-line hover:border-accent
        transition-colors
        group 
      `}
    >
      {/* Header */}
      <div className="mb-6">
        <h3 className="font-display text-lg font-bold tracking-wide text-foreground">{title}</h3>
        {description && (
          <p className="text-sm text-cream-dim mt-1">{description}</p>
        )}
      </div>

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  )
}
