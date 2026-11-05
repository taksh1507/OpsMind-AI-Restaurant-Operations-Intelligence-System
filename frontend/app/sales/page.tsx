'use client'
import useSWR from 'swr'
import { StatCard } from '@/components/ui'
import { analyticsFetcher, type SalesSummary } from '@/lib/analytics-api'
import { formatRupee, formatPercentage } from '@/lib/format-utils'

interface Hourly { date: string; hours: { hour: number; revenue: number; transactions: number }[] }
interface Daily { daily_trends: { date: string; revenue: number; cost: number }[] }
export default function SalesPage() {
  const { data: summary, error: summaryError } = useSWR<SalesSummary>('/analytics/summary', analyticsFetcher, { refreshInterval: 60000 })
  const { data: hourly, error: hourlyError } = useSWR<Hourly>('/analytics/hourly-sales', analyticsFetcher, { refreshInterval: 60000 })
  const { data: daily, error: dailyError } = useSWR<Daily>('/analytics/daily-trends?days=7', analyticsFetcher, { refreshInterval: 60000 })
  if (summaryError || hourlyError || dailyError) return <p role="alert" className="p-8">Unable to load sales analytics. Please try again.</p>
  if (!summary || !hourly || !daily) return <p className="p-8">Loading sales…</p>
  const metrics = summary.metrics
  const maxRevenue = Math.max(1, ...hourly.hours.map(hour => hour.revenue))
  return <div className="p-8 space-y-6">
    <h1 className="text-3xl font-semibold">Sales analytics</h1>
    <p className="text-cream-dim">Last 30 days · INR · sales exclude tax. Refreshes every minute.</p>
    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard title="Revenue" value={formatRupee(metrics.total_revenue_inr)} change={metrics.revenue_change ?? undefined} description="vs previous equal period" />
      <StatCard title="Average order value" value={formatRupee(metrics.transaction_count ? metrics.total_revenue_inr / metrics.transaction_count : 0)} />
      <StatCard title="Completed orders" value={metrics.transaction_count} />
      <StatCard title="Estimated COGS ratio" value={formatPercentage(metrics.total_revenue_inr ? metrics.cost_of_goods_sold_inr / metrics.total_revenue_inr * 100 : 0)} description="Uses current menu costs" />
    </div>
    {metrics.transaction_count === 0 && <p>No recorded sales in this period.</p>}
    <section className="bg-surface border border-line p-5 space-y-3"><h2 className="text-xl">Hourly sales · {hourly.date} UTC</h2>
      {!hourly.hours.some(hour => hour.transactions) && <p>No sales recorded today.</p>}
      {hourly.hours.map(hour => <div key={hour.hour}><div className="flex justify-between text-sm"><span>{String(hour.hour).padStart(2, '0')}:00</span><span>{formatRupee(hour.revenue)} · {hour.transactions} orders</span></div><div className="h-2 bg-background rounded"><div className="h-2 bg-accent rounded" style={{ width: `${hour.revenue / maxRevenue * 100}%` }} /></div></div>)}
    </section>
    <section className="bg-surface border border-line p-5"><h2 className="text-xl mb-3">Daily sales · past 7 days (UTC)</h2>
      {daily.daily_trends.length ? <table className="w-full text-left"><thead><tr><th>Date</th><th>Revenue</th><th>Estimated COGS</th></tr></thead><tbody>{daily.daily_trends.map(day => <tr key={day.date}><td>{day.date}</td><td>{formatRupee(day.revenue)}</td><td>{formatRupee(day.cost)}</td></tr>)}</tbody></table> : <p>No daily history available.</p>}
    </section>
  </div>
}
