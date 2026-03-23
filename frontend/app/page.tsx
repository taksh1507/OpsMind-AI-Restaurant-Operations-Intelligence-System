'use client'

import { StatCard } from '@/components/ui'
import {
  TrendingUp,
  DollarSign,
  Zap,
  Target,
  Users,
  AlertCircle
} from 'lucide-react'

export default function Home() {
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
          value="$4,280"
          change={12}
          description="vs last week"
          icon={<DollarSign size={24} />}
        />
        <StatCard
          title="Profit Margin"
          value="34.2%"
          change={-2}
          description="vs average"
          icon={<TrendingUp size={24} />}
        />
        <StatCard
          title="AI Confidence"
          value="87%"
          change={8}
          description="insight accuracy"
          icon={<Zap size={24} />}
        />
        <StatCard
          title="Active Orders"
          value="24"
          change={3}
          description="current in queue"
          icon={<Target size={24} />}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StatCard
          title="Staff Efficiency"
          value="92%"
          change={5}
          description="labor-to-sales ratio"
          icon={<Users size={24} />}
        />
        <StatCard
          title="System Alerts"
          value="3"
          change={0}
          description="low inventory items"
          icon={<AlertCircle size={24} />}
        />
      </div>

      {/* Insights Section */}
      <div className="mt-12 p-6 rounded-xl border border-electric-500/30 bg-slate-800/30 backdrop-blur-sm">
        <h2 className="text-xl font-semibold text-slate-50 mb-4">
          🤖 AI Insights Summary
        </h2>
        <div className="space-y-3 text-slate-300 text-sm">
          <p>
            • <span className="text-electric-400">Top Performer:</span> Margherita Pizza (23 units, +18% vs avg)
          </p>
          <p>
            • <span className="text-electric-400">Underperformer:</span> Caesar Salad (4 units, -35% vs avg)
          </p>
          <p>
            • <span className="text-electric-400">Weather Impact:</span> Rainy weather detected - expect 15% spike in hot beverages
          </p>
          <p>
            • <span className="text-electric-400">Recommendation:</span> 7% price increase on Margherita recommended (ROI: +$120/month)
          </p>
        </div>
      </div>
    </div>
  )
}
            Deploy Now
          </a>
          <a
            className="flex h-12 w-full items-center justify-center rounded-full border border-solid border-black/[.08] px-5 transition-colors hover:border-transparent hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-[#1a1a1a] md:w-[158px]"
            href="https://nextjs.org/docs?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
            target="_blank"
            rel="noopener noreferrer"
          >
            Documentation
          </a>
        </div>
      </main>
    </div>
  );
}
