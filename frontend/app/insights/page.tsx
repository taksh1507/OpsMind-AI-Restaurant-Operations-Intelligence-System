'use client'

import { StatCard, RevenueChart, TopItemsChart, AISummaryBanner } from '@/components/ui'
import { Sparkles, Brain, TrendingUp, AlertTriangle } from 'lucide-react'

export default function InsightsPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-accent/20 pb-6">
        <h1 className="font-display text-4xl font-bold text-foreground mb-1 flex items-center gap-3">
          <Sparkles size={32} className="text-accent" />
          AI Insights
        </h1>
        <p className="text-cream-dim">
          Visual Intelligence Layer â€¢ Real-time analytics powered by Gemini 1.5 Flash
        </p>
      </div>

      {/* AI Strategic Insight Banner */}
      <div>
        <AISummaryBanner />
      </div>

      {/* Visual Charts Section */}
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-foreground flex items-center gap-2">
          ðŸ“Š Visual Intelligence Layer
        </h2>

        {/* Revenue vs Cost Area Chart */}
        <RevenueChart />

        {/* Top Selling Items Bar Chart */}
        <TopItemsChart />
      </div>

      {/* AI Metrics */}
      <div>
        <div className="flex items-center gap-2.5 mb-5">
          <span className="w-[3px] h-[18px] bg-accent rounded-[2px]" />
          <h2 className="font-display text-lg font-bold tracking-wide text-foreground">Performance Metrics</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <StatCard
            title="Confidence Score"
            value="87%"
            description="insight accuracy"
            icon={<Brain size={24} />}
          />
          <StatCard
            title="Active Recommendations"
            value="12"
            description="pending implementation"
            icon={<Sparkles size={24} />}
          />
          <StatCard
            title="ROI Projected"
            value="$4,850"
            description="from implemented suggestions"
            icon={<TrendingUp size={24} />}
          />
        </div>
      </div>

      {/* Recommendations */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-foreground">Top Recommendations</h2>

        {[
          {
            title: 'Price Increase Opportunity',
            description: 'Margherita Pizza shows high demand and low elasticity. Recommend 7% price increase.',
            impact: '+$120/month',
            priority: 'high',
          },
          {
            title: 'Staff Optimization',
            description: '3-5 PM shows 40% slower service. Recommend temporary 2-person increase during peak.',
            impact: '+$85/month',
            priority: 'medium',
          },
          {
            title: 'Menu Rebalancing',
            description: 'Caesar Salad underperforming. Consider repositioning or reformulating.',
            impact: '+$145/month',
            priority: 'high',
          },
          {
            title: 'Weather-Based Promotion',
            description: 'Rainy days show +18% hot beverage spike. Create seasonal bundles.',
            impact: '+$95/month',
            priority: 'medium',
          },
        ].map((rec, idx) => (
          <div
            key={idx}
            className={`p-6 rounded-[3px] border  transition-all hover:border-accent ${
              rec.priority === 'high'
                ? 'border-red-500/30 bg-red-900/10'
                : 'border-line bg-surface'
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-start gap-3 flex-1">
                {rec.priority === 'high' && (
                  <AlertTriangle size={20} className="text-red-400 mt-1 flex-shrink-0" />
                )}
                <div>
                  <h3 className="text-lg font-semibold text-foreground">{rec.title}</h3>
                  <p className="text-cream-dim mt-1">{rec.description}</p>
                </div>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-sm font-semibold whitespace-nowrap ml-4 ${
                  rec.priority === 'high'
                    ? 'bg-red-500/20 text-red-300'
                    : 'bg-accent/20 text-electric-300'
                }`}
              >
                {rec.impact}
              </span>
            </div>
            <button className="mt-4 px-4 py-2 rounded-[3px] bg-electric-600/20 border border-line hover:bg-electric-600/30 text-electric-300 hover:text-electric-200 transition-colors text-sm font-display font-semibold tracking-wide">
              View Details â†’
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
