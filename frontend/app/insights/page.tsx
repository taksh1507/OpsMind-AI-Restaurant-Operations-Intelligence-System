'use client'
import useSWR from 'swr'
import { StatCard, RevenueChart, TopItemsChart, AISummaryBanner } from '@/components/ui'
import { analyticsFetcher, type SalesSummary } from '@/lib/analytics-api'

interface Recommendation { id: number; category: string; content: string; status: string }
interface RecommendationSummary { pending: number; accepted: number; rejected: number; verified: number; model: string }
export default function InsightsPage() {
  const { data: counts, error: countError } = useSWR<RecommendationSummary>('/recommendations/summary', analyticsFetcher)
  const { data: recommendations, error: listError } = useSWR<Recommendation[]>('/recommendations?status_filter=Pending&limit=20', analyticsFetcher)
  const { data: sales, error: salesError } = useSWR<SalesSummary>('/analytics/summary', analyticsFetcher)
  if (countError || listError || salesError) return <p role="alert" className="p-8">Unable to load insights. Please try again.</p>
  if (!counts || !recommendations || !sales) return <p className="p-8">Loading insights…</p>
  return <div className="p-8 space-y-6">
    <h1 className="text-3xl font-semibold">AI insights</h1>
    <p className="text-cream-dim">Configured Claude model: {counts.model}</p>
    {sales.metrics.transaction_count ? <AISummaryBanner /> : <p>No sales available for analysis. Record sales to generate insights.</p>}
    <div className="grid md:grid-cols-3 gap-4">
      <StatCard title="Pending recommendations" value={counts.pending} />
      <StatCard title="Accepted recommendations" value={counts.accepted} />
      <StatCard title="Verified recommendations" value={counts.verified} description="Recommendations with a recorded impact verification" />
    </div>
    <RevenueChart /><TopItemsChart />
    <section className="space-y-3"><h2 className="text-xl">Pending recommendations</h2>
      {recommendations.length === 0 && <p>No pending recommendations.</p>}
      {recommendations.map(item => <article key={item.id} className="p-5 border border-line bg-surface rounded"><h3 className="font-semibold">{item.category}</h3><p>{item.content}</p><p className="text-sm text-cream-dim">{item.status}</p></article>)}
      {counts.pending > recommendations.length && <p>Showing the latest {recommendations.length} of {counts.pending} pending recommendations.</p>}
    </section>
  </div>
}
