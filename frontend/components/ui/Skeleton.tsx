'use client'

export function StatCardSkeleton() {
  return (
    <div className="relative overflow-hidden rounded-xl p-6 bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-electric-500/30">
      {/* Animated pulse effect */}
      <div className="animate-pulse space-y-4">
        {/* Title skeleton */}
        <div className="h-3 bg-slate-700/50 rounded w-24"></div>

        {/* Value skeleton */}
        <div className="h-10 bg-slate-700/50 rounded w-32"></div>

        {/* Footer skeleton */}
        <div className="flex items-center gap-2 pt-4 border-t border-electric-500/10">
          <div className="h-6 bg-slate-700/50 rounded w-16"></div>
          <div className="h-3 bg-slate-700/50 rounded flex-1"></div>
        </div>
      </div>
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      {/* Header skeleton */}
      <div className="border-b border-electric-500/20 pb-6">
        <div className="h-10 bg-slate-700/50 rounded w-48 mb-2"></div>
        <div className="h-4 bg-slate-700/50 rounded w-96"></div>
      </div>

      {/* Stats grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>

      {/* Secondary stats skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {Array.from({ length: 2 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>

      {/* Insights section skeleton */}
      <div className="p-6 rounded-xl border border-electric-500/30 bg-slate-800/30 animate-pulse">
        <div className="h-6 bg-slate-700/50 rounded w-40 mb-4"></div>
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-4 bg-slate-700/50 rounded"></div>
          ))}
        </div>
      </div>
    </div>
  )
}
