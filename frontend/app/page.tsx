'use client'

import { StatCard, DashboardSkeleton } from '@/components/ui'
import { useDashboardStats } from '@/hooks/useDashboardStats'
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
  const { stats, isLoading, isError, error } = useDashboardStats()

  // Show skeleton while loading
  if (isLoading) {
    return <DashboardSkeleton />
  }

  // Show error state
  if (isError || !stats) {
    return (
      <div className="space-y-8">
        <div className="border-b border-electric-500/20 pb-6">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2">
            Dashboard
          </h1>
          <p className="text-slate-400">Unable to load dashboard data</p>
        </div>

        <div className="p-6 rounded-xl border border-red-500/30 bg-red-900/10">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-red-400 flex-shrink-0 mt-1" size={20} />
            <div>
              <h3 className="text-red-300 font-semibold mb-1">Failed to Load Data</h3>
              <p className="text-red-300/70 text-sm">
                {error?.message || 'Please check if the backend API is running on http://localhost:8000'}
              </p>
              <button
                onClick={() => window.location.reload()}
                className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors text-sm font-medium"
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
      {/* Welcome Header */}
      <div className="border-b border-electric-500/20 pb-6">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2">
          Welcome Back
        </h1>
        <p className="text-slate-400">
          Here's what's happening with your restaurant today
        </p>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Today's Revenue"
          value={formatRupee(stats.total_revenue_inr)}
          change={stats.revenue_change}
          description="vs last week"
          icon={<IndianRupee size={24} />}
        />
        <StatCard
          title="Profit Margin"
          value={formatPercentage(stats.profit_margin)}
          change={stats.profit_change}
          description="vs average"
          icon={<TrendingUp size={24} />}
        />
        <StatCard
          title="AI Confidence"
          value={formatPercentage(stats.ai_confidence_score)}
          change={stats.confidence_change}
          description="insight accuracy"
          icon={<Zap size={24} />}
        />
        <StatCard
          title="Active Orders"
          value={stats.active_orders}
          description="current in queue"
          icon={<Target size={24} />}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StatCard
          title="Staff Efficiency"
          value={`${stats.staff_efficiency.toFixed(1)}%`}
          description="labor-to-sales ratio"
          icon={<Users size={24} />}
        />
        <StatCard
          title="System Alerts"
          value={stats.system_alerts}
          description="items needing attention"
          icon={<AlertCircle size={24} />}
        />
      </div>

      {/* Insights Section */}
      <div className="mt-12 p-6 rounded-xl border border-electric-500/30 bg-slate-800/30 backdrop-blur-sm">
        <h2 className="text-xl font-semibold text-slate-50 mb-4">
          🤖 Real-Time Analytics
        </h2>
        <div className="space-y-3 text-slate-300 text-sm">
          <p>
            <span className="text-electric-400 font-semibold">Status:</span> All systems operational and connected to backend API
          </p>
          <p>
            <span className="text-electric-400 font-semibold">Data Source:</span> FastAPI Backend (Real-Time)
          </p>
          <p>
            <span className="text-electric-400 font-semibold">Cache Policy:</span> 1-minute revalidation with SWR
          </p>
          <p>
            <span className="text-electric-400 font-semibold">Authentication:</span> JWT Bearer Token
          </p>
        </div>
      </div>
    </div>
  )
}
