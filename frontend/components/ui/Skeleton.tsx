'use client'

export function StatCardSkeleton() {
  return (
    <div className="relative overflow-hidden rounded-[3px] p-6 bg-surface ticket-perf border border-line">
      {/* Animated pulse effect */}
      <div className="animate-pulse space-y-4">
        {/* Title skeleton */}
        <div className="h-3 bg-slate-700/50 rounded w-24"></div>

        {/* Value skeleton */}
        <div className="h-10 bg-slate-700/50 rounded w-32"></div>

        {/* Footer skeleton */}
        <div className="flex items-center gap-2 pt-4 border-t border-accent/10">
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
      <div className="border-b border-accent/20 pb-6">
        <div className="h-10 bg-slate-700/50 rounded w-48 mb-2"></div>
        <div className="h-4 bg-slate-700/50 rounded w-96"></div>
      </div>

      {/* Stats grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>

      {/* Secondary stats skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Array.from({ length: 2 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>

      {/* Insights section skeleton */}
      <div className="ticket-perf relative p-6 rounded-[3px] border border-line bg-surface animate-pulse">
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
