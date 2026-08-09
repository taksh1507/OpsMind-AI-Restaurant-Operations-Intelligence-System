'use client'

import { StatCard, DashboardSkeleton } from '@/components/ui'
import { useDashboardStats } from '@/hooks/useDashboardStats'
import { useAuth } from '@/hooks/useAuth'
import { formatRupee, formatPercentage } from '@/lib/format-utils'
import {
  TrendingUp,
  IndianRupee,
  Zap,
  Target,
  Users,
  AlertCircle
} from 'lucide-react'

export default function Home() {
  const { isAuthenticated } = useAuth()
  const { stats, isLoading, isError, error } = useDashboardStats()

  // Show nothing while checking authentication
  if (isAuthenticated === null) {
    return <DashboardSkeleton />
  }

  // Show skeleton while loading
  if (isLoading) {
    return <DashboardSkeleton />
  }

  // Show error state
  if (isError || !stats) {
    return (
      <div className="space-y-8">
        <div className="border-b border-slate-700 pb-6">
          <h1 className="font-display text-4xl font-bold text-slate-50 mb-1">
            Tonight&rsquo;s Pass
          </h1>
          <p className="text-slate-400">Unable to load dashboard data</p>
        </div>

        <div className="p-6 rounded-[3px] border border-alert/40 bg-alert/5">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-alert flex-shrink-0 mt-1" size={20} />
            <div>
              <h3 className="font-display text-alert font-semibold mb-1 tracking-wide">Failed to Load Data</h3>
              <p className="text-alert/80 text-sm">
                {error?.message || 'Please check if the backend API is running on http://localhost:8000'}
              </p>
              <button
                onClick={() => window.location.reload()}
                className="mt-3 px-4 py-2 bg-alert hover:bg-alert/80 text-white rounded-[3px] transition-colors text-sm font-medium"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-slate-700 pb-6">
        <h1 className="font-display text-4xl font-bold text-slate-50 mb-1">
          Tonight&rsquo;s Pass
        </h1>
        <p className="text-slate-400">
          Here&rsquo;s what&rsquo;s happening in the kitchen right now
        </p>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Today's Revenue"
          value={formatRupee(stats.total_revenue_inr)}
          change={stats.revenue_change}
          description="vs last week"
          icon={<IndianRupee size={18} />}
        />
        <StatCard
          title="Profit Margin"
          value={formatPercentage(stats.profit_margin)}
          change={stats.profit_change}
          description="vs average"
          icon={<TrendingUp size={18} />}
        />
        <StatCard
          title="AI Confidence"
          value={formatPercentage(stats.ai_confidence_score)}
          change={stats.confidence_change}
          description="insight accuracy"
          icon={<Zap size={18} />}
        />
        <StatCard
          title="Active Orders"
          value={stats.active_orders}
          description="current in queue"
          icon={<Target size={18} />}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StatCard
          title="Staff Efficiency"
          value={`${stats.staff_efficiency.toFixed(1)}%`}
          description="labor-to-sales ratio"
          icon={<Users size={18} />}
        />
        <StatCard
          title="System Alerts"
          value={stats.system_alerts}
          description="items needing attention"
          icon={<AlertCircle size={18} />}
        />
      </div>

      {/* Insights Panel */}
      <div className="mt-4 p-6 rounded-[3px] border border-slate-700 bg-slate-900">
        <div className="flex items-center gap-2.5 mb-4">
          <span className="w-[3px] h-[18px] bg-electric-500 rounded-sm" />
          <h2 className="font-display text-lg font-bold tracking-wide text-slate-50">
            Real-Time Analytics
          </h2>
        </div>
        <div className="divide-y divide-slate-700">
          {[
            ['Status', 'All systems operational'],
            ['Data Source', 'FastAPI backend (live)'],
            ['Cache Policy', '60s revalidation · SWR'],
            ['Authentication', 'JWT bearer token'],
          ].map(([k, v]) => (
            <div key={k} className="flex items-center justify-between py-2.5 text-sm">
              <span className="font-display text-xs font-semibold uppercase tracking-wide text-slate-400">{k}</span>
              <span className="font-data text-slate-100 text-[13px]">{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
