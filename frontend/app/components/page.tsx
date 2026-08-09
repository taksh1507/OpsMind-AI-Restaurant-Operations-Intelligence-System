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
      <div className="border-b border-accent/20 pb-6">
        <h1 className="font-display text-4xl font-bold text-foreground mb-1">
          Component Gallery
        </h1>
        <p className="text-cream-dim">
          Enterprise-grade UI components with glassmorphism and glow effects
        </p>
      </div>

      {/* StatCard Showcase */}
      <div>
        <div className="flex items-center gap-2.5 mb-5">
          <span className="w-[3px] h-[18px] bg-accent rounded-[2px]" />
          <h2 className="font-display text-lg font-bold tracking-wide text-foreground">StatCard Variants</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
        <div className="flex items-center gap-2.5 mb-5">
          <span className="w-[3px] h-[18px] bg-accent rounded-[2px]" />
          <h2 className="font-display text-lg font-bold tracking-wide text-foreground">Gradient Badges</h2>
        </div>
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
        <div className="flex items-center gap-2.5 mb-5">
          <span className="w-[3px] h-[18px] bg-accent rounded-[2px]" />
          <h2 className="font-display text-lg font-bold tracking-wide text-foreground">Progress Indicators</h2>
        </div>
        <div className="ticket-perf relative p-6 rounded-[3px] border border-line bg-surface  space-y-6">
          <ProgressBar label="AI Model Confidence" value={87} color="electric" />
          <ProgressBar label="System Optimization" value={72} color="warning" />
          <ProgressBar label="API Response Time" value={95} color="success" />
          <ProgressBar label="Database Load" value={58} color="warning" />
          <ProgressBar label="Error Rate" value={8} color="error" />
        </div>
      </div>

      {/* Chart Card Examples */}
      <div>
        <div className="flex items-center gap-2.5 mb-5">
          <span className="w-[3px] h-[18px] bg-accent rounded-[2px]" />
          <h2 className="font-display text-lg font-bold tracking-wide text-foreground">Chart Cards</h2>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ChartCard title="Daily Revenue Trend" description="Last 7 days">
            <div className="h-40 flex items-end justify-around">
              {[65, 78, 92, 88, 95, 110, 105].map((height, idx) => (
                <div
                  key={idx}
                  className="w-8 bg-accent rounded-t-md transition-all hover:from-electric-400 hover:to-electric-300 hover:"
                  style={{ height: `${height * 1.5}px` }}
                />
              ))}
            </div>
          </ChartCard>

          <ChartCard title="Customer Satisfaction" description="Weekly metrics">
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-cream-dim">Very Satisfied</span>
                  <span className="text-sm font-semibold text-electric-300">68%</span>
                </div>
                <div className="w-full h-2 bg-surface rounded-full overflow-hidden border border-line">
                  <div className="h-full w-[68%] bg-success" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-cream-dim">Satisfied</span>
                  <span className="text-sm font-semibold text-electric-300">24%</span>
                </div>
                <div className="w-full h-2 bg-surface rounded-full overflow-hidden border border-line">
                  <div className="h-full w-[24%] bg-warning" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-cream-dim">Needs Improvement</span>
                  <span className="text-sm font-semibold text-electric-300">8%</span>
                </div>
                <div className="w-full h-2 bg-surface rounded-full overflow-hidden border border-line">
                  <div className="h-full w-[8%] bg-alert" />
                </div>
              </div>
            </div>
          </ChartCard>
        </div>
      </div>

      {/* Advanced Card Patterns */}
      <div>
        <div className="flex items-center gap-2.5 mb-5">
          <span className="w-[3px] h-[18px] bg-accent rounded-[2px]" />
          <h2 className="font-display text-lg font-bold tracking-wide text-foreground">Advanced Patterns</h2>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Feature Card */}
          <div
            className={`
              relative overflow-hidden rounded-[3px] p-6
              bg-surface ticket-perf border border-line hover:border-accent
              transition-all duration-300
              hover:
              group 
            `}
          >
            <div className="absolute top-0 right-0 w-40 h-40 bg-accent/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative z-10">
              <CheckCircle className="text-green-400 mb-4" size={28} />
              <h3 className="text-lg font-semibold text-foreground mb-2">Premium Features</h3>
              <p className="text-cream-dim text-sm">
                Advanced analytics, real-time insights, and AI-powered recommendations
              </p>
            </div>
          </div>

          {/* Alert Card */}
          <div
            className={`
              relative overflow-hidden rounded-[3px] p-6
              bg-surface ticket-perf border border-red-500/30 hover:border-red-500/60
              transition-all duration-300
              group 
            `}
          >
            <div className="absolute top-0 right-0 w-40 h-40 bg-red-500/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative z-10">
              <AlertCircle className="text-red-400 mb-4" size={28} />
              <h3 className="text-lg font-semibold text-foreground mb-2">System Alert</h3>
              <p className="text-cream-dim text-sm">
                Lower than expected feature adoption. Review onboarding process.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
