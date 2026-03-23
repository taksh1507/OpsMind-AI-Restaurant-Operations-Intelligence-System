'use client'

import { StatCard, GradientBadge, ProgressBar, ChartCard } from '@/components/ui'
import {
  BarChart3,
  DollarSign,
  Users,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Zap,
  Eye,
} from 'lucide-react'

export default function ComponentsShowcase() {
  return (
    <div className="space-y-12">
      {/* Header */}
      <div className="border-b border-electric-500/20 pb-6">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2">
          Component Gallery
        </h1>
        <p className="text-slate-400">
          Enterprise-grade UI components with glassmorphism and glow effects
        </p>
      </div>

      {/* StatCard Showcase */}
      <div>
        <h2 className="text-2xl font-semibold text-slate-50 mb-6">StatCard Variants</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Revenue"
            value="$12,450"
            change={18}
            description="vs last month"
            icon={<DollarSign size={24} />}
          />
          <StatCard
            title="Growth"
            value="23%"
            change={12}
            description="year-over-year"
            icon={<TrendingUp size={24} />}
          />
          <StatCard
            title="Users"
            value="1,284"
            change={-5}
            description="monthly active"
            icon={<Users size={24} />}
          />
          <StatCard
            title="Performance"
            value="94%"
            change={7}
            description="uptime"
            icon={<Eye size={24} />}
          />
        </div>
      </div>

      {/* Badge Showcase */}
      <div>
        <h2 className="text-2xl font-semibold text-slate-50 mb-6">Gradient Badges</h2>
        <div className="flex flex-wrap gap-4">
          <GradientBadge label="Success" type="success" />
          <GradientBadge label="Warning" type="warning" />
          <GradientBadge label="Error" type="error" />
          <GradientBadge label="Info" type="info" />
          <GradientBadge label="Featured" type="info" />
          <GradientBadge label="In Progress" type="warning" />
        </div>
      </div>

      {/* Progress Bars */}
      <div>
        <h2 className="text-2xl font-semibold text-slate-50 mb-6">Progress Indicators</h2>
        <div className="p-6 rounded-xl border border-electric-500/30 bg-slate-800/30 backdrop-blur-sm space-y-6">
          <ProgressBar label="AI Model Confidence" value={87} color="electric" />
          <ProgressBar label="System Optimization" value={72} color="warning" />
          <ProgressBar label="API Response Time" value={95} color="success" />
          <ProgressBar label="Database Load" value={58} color="warning" />
          <ProgressBar label="Error Rate" value={8} color="error" />
        </div>
      </div>

      {/* Chart Card Examples */}
      <div>
        <h2 className="text-2xl font-semibold text-slate-50 mb-6">Chart Cards</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartCard title="Daily Revenue Trend" description="Last 7 days">
            <div className="h-40 flex items-end justify-around">
              {[65, 78, 92, 88, 95, 110, 105].map((height, idx) => (
                <div
                  key={idx}
                  className="w-8 bg-gradient-to-t from-electric-500 to-electric-400 rounded-t-md transition-all hover:from-electric-400 hover:to-electric-300 hover:shadow-glow-electric"
                  style={{ height: `${height * 1.5}px` }}
                />
              ))}
            </div>
          </ChartCard>

          <ChartCard title="Customer Satisfaction" description="Weekly metrics">
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-slate-300">Very Satisfied</span>
                  <span className="text-sm font-semibold text-electric-300">68%</span>
                </div>
                <div className="w-full h-2 bg-slate-900/50 rounded-full overflow-hidden border border-slate-800">
                  <div className="h-full w-[68%] bg-gradient-to-r from-green-500 tp-emerald-400" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-slate-300">Satisfied</span>
                  <span className="text-sm font-semibold text-electric-300">24%</span>
                </div>
                <div className="w-full h-2 bg-slate-900/50 rounded-full overflow-hidden border border-slate-800">
                  <div className="h-full w-[24%] bg-gradient-to-r from-yellow-500 to-orange-400" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-slate-300">Needs Improvement</span>
                  <span className="text-sm font-semibold text-electric-300">8%</span>
                </div>
                <div className="w-full h-2 bg-slate-900/50 rounded-full overflow-hidden border border-slate-800">
                  <div className="h-full w-[8%] bg-gradient-to-r from-red-500 to-pink-400" />
                </div>
              </div>
            </div>
          </ChartCard>
        </div>
      </div>

      {/* Advanced Card Patterns */}
      <div>
        <h2 className="text-2xl font-semibold text-slate-50 mb-6">Advanced Patterns</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Feature Card */}
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
            <div className="absolute top-0 right-0 w-40 h-40 bg-electric-500/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative z-10">
              <CheckCircle className="text-green-400 mb-4" size={28} />
              <h3 className="text-lg font-semibold text-slate-50 mb-2">Premium Features</h3>
              <p className="text-slate-400 text-sm">
                Advanced analytics, real-time insights, and AI-powered recommendations
              </p>
            </div>
          </div>

          {/* Alert Card */}
          <div
            className={`
              relative overflow-hidden rounded-xl p-6
              bg-gradient-to-br from-red-900/20 to-slate-900/50
              border border-red-500/30 hover:border-red-500/60
              transition-all duration-300
              group backdrop-blur-sm
            `}
          >
            <div className="absolute top-0 right-0 w-40 h-40 bg-red-500/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative z-10">
              <AlertCircle className="text-red-400 mb-4" size={28} />
              <h3 className="text-lg font-semibold text-slate-50 mb-2">System Alert</h3>
              <p className="text-slate-400 text-sm">
                Lower than expected feature adoption. Review onboarding process.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
