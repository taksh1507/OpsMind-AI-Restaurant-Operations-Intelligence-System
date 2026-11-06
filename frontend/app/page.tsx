'use client'
import { StatCard, DashboardSkeleton } from '@/components/ui'
import { useDashboardStats } from '@/hooks/useDashboardStats'
import { useAuth } from '@/hooks/useAuth'
import { formatRupee, formatPercentage } from '@/lib/format-utils'

export default function Home() {
  const { isAuthenticated } = useAuth()
  const { stats, period, isLoading, isError } = useDashboardStats()
  if (isAuthenticated === null || isLoading) return <DashboardSkeleton />
  if (isError || !stats) return <p role="alert" className="p-8">Unable to load dashboard data. Please try again.</p>
  return <div className="p-8 space-y-6">
    <h1 className="text-3xl font-semibold">Restaurant overview</h1>
    <p className="text-cream-dim">Last 30 days · UTC · recorded sales, excluding tax</p>
    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard title="Revenue" value={formatRupee(stats.total_revenue_inr)} change={stats.revenue_change ?? undefined} description="vs previous equal period" />
      <StatCard title="Gross profit" value={formatRupee(stats.total_profit_inr)} change={stats.profit_change ?? undefined} description="Current menu cost estimate" />
      <StatCard title="Gross margin" value={formatPercentage(stats.profit_margin_percent)} />
      <StatCard title="Completed orders" value={stats.transaction_count} description="Recorded transactions in this period" />
    </div>
    {stats.transaction_count === 0 && <p>No recorded sales in this period. Add sales to see performance data.</p>}
    {period && <p className="text-sm text-cream-dim">{period.start_date} to {period.end_date} (end exclusive)</p>}
  </div>
}
