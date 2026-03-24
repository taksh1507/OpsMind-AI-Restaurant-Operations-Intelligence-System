'use client'

import { StatCard, RevenueChart, TopItemsChart, AISummaryBanner } from '@/components/ui'
import { Sparkles, Brain, TrendingUp, AlertTriangle } from 'lucide-react'

export default function InsightsPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-electric-500/20 pb-6">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2 flex items-center gap-3">
          <Sparkles size={32} className="text-electric-400" />
          AI Insights
        </h1>
        <p className="text-slate-400">
          Visual Intelligence Layer • Real-time analytics powered by Gemini 1.5 Flash
        </p>
      </div>

      {/* AI Strategic Insight Banner */}
      <div>
        <AISummaryBanner />
      </div>

      {/* Visual Charts Section */}
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold text-slate-50 flex items-center gap-2">
          📊 Visual Intelligence Layer
        </h2>

        {/* Revenue vs Cost Area Chart */}
        <RevenueChart />

        {/* Top Selling Items Bar Chart */}
        <TopItemsChart />
      </div>

      {/* AI Metrics */}
      <div>
        <h2 className="text-xl font-semibold text-slate-50 mb-4">Performance Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
        <h2 className="text-2xl font-semibold text-slate-50">Top Recommendations</h2>

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
            className={`p-6 rounded-xl border backdrop-blur-sm transition-all hover:border-electric-500/60 ${
              rec.priority === 'high'
                ? 'border-red-500/30 bg-red-900/10'
                : 'border-electric-500/30 bg-slate-800/30'
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-start gap-3 flex-1">
                {rec.priority === 'high' && (
                  <AlertTriangle size={20} className="text-red-400 mt-1 flex-shrink-0" />
                )}
                <div>
                  <h3 className="text-lg font-semibold text-slate-50">{rec.title}</h3>
                  <p className="text-slate-400 mt-1">{rec.description}</p>
                </div>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-sm font-semibold whitespace-nowrap ml-4 ${
                  rec.priority === 'high'
                    ? 'bg-red-500/20 text-red-300'
                    : 'bg-electric-500/20 text-electric-300'
                }`}
              >
                {rec.impact}
              </span>
            </div>
            <button className="mt-4 px-4 py-2 rounded-lg bg-electric-600/20 border border-electric-500/30 hover:bg-electric-600/30 text-electric-300 hover:text-electric-200 transition-colors text-sm font-medium">
              View Details →
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
