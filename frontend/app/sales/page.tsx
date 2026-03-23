'use client'

import { StatCard } from '@/components/ui'
import { TrendingUp, BarChart3 } from 'lucide-react'

export default function SalesPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-electric-500/20 pb-6">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2 flex items-center gap-3">
          <BarChart3 size={32} className="text-electric-400" />
          Sales Analytics
        </h1>
        <p className="text-slate-400">
          Real-time sales tracking and performance metrics
        </p>
      </div>

      {/* Sales KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Weekly Revenue"
          value="$28,450"
          change={18}
          description="vs last week"
          icon={<TrendingUp size={24} />}
        />
        <StatCard
          title="Avg Order Value"
          value="$42.80"
          change={-3}
          description="down from $44.15"
          icon={<TrendingUp size={24} />}
        />
        <StatCard
          title="Total Orders"
          value="664"
          change={12}
          description="this week"
          icon={<TrendingUp size={24} />}
        />
        <StatCard
          title="COGS Ratio"
          value="32.4%"
          change={-2}
          description="improved margins"
          icon={<TrendingUp size={24} />}
        />
      </div>

      {/* Hourly Sales Trend */}
      <div className="p-6 rounded-xl border border-electric-500/30 bg-slate-800/30 backdrop-blur-sm">
        <h2 className="text-xl font-semibold text-slate-50 mb-6">
          Today's Hourly Performance
        </h2>
        <div className="space-y-4">
          {Array.from({ length: 8 }).map((_, idx) => {
            const hour = 10 + idx
            const sales = Math.floor(Math.random() * 4000) + 1000
            const percentage = (sales / 5000) * 100
            return (
              <div key={idx} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">{hour}:00 - {hour + 1}:00</span>
                  <span className="text-electric-400 font-semibold">${sales}</span>
                </div>
                <div className="w-full bg-slate-900/50 rounded-full h-2 overflow-hidden border border-slate-800">
                  <div
                    className="h-full bg-gradient-to-r from-electric-500 to-electric-400 transition-all duration-500"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
