'use client'

import { useEffect, useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import apiClient from '@/lib/api-client'
import { formatRupee } from '@/lib/format-utils'
import { AlertCircle } from 'lucide-react'

interface DailyTrend {
  date: string
  revenue: number
  cost: number
}

interface IChartData {
  status: string
  daily_trends: DailyTrend[]
}

const COLORS = {
  revenue: '#00D9FF', // Electric Blue
  cost: '#FF6B6B', // Deep Coral (adjusted for visibility)
}

export function RevenueChart() {
  const [data, setData] = useState<DailyTrend[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDailyTrends = async () => {
      try {
        setLoading(true)
        const response = await apiClient.get<IChartData>('/analytics/daily-trends', {
          params: { days: 14 },
        })

        if (response.data.status === 'success') {
          setData(response.data.daily_trends)
          setError(null)
        } else {
          setError('Failed to load chart data')
        }
      } catch (err) {
        console.error('Error fetching daily trends:', err)
        setError('Unable to load chart data')
      } finally {
        setLoading(false)
      }
    }

    fetchDailyTrends()
  }, [])

  if (loading) {
    return (
      <div className="h-80 w-full bg-slate-900/30 border border-slate-700/50 rounded-xl p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-electric-500/30 border-t-electric-400 rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">Loading chart data...</p>
        </div>
      </div>
    )
  }

  if (error || data.length === 0) {
    return (
      <div className="h-80 w-full bg-slate-900/30 border border-slate-700/50 rounded-xl p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <AlertCircle size={24} className="text-red-400" />
          <p className="text-slate-300">{error || 'No data available'}</p>
        </div>
      </div>
    )
  }

  // Format data for Recharts
  const chartData = data.map((item) => ({
    ...item,
    date: new Date(item.date).toLocaleDateString('en-IN', {
      month: 'short',
      day: 'numeric',
    }),
  }))

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900/95 border border-electric-500/30 rounded-lg p-3 backdrop-blur-md">
          <p className="text-slate-300 text-sm font-medium">{payload[0].payload.date}</p>
          {payload.map((entry: any, index: number) => (
            <p
              key={index}
              className="text-sm font-medium"
              style={{ color: entry.color }}
            >
              {entry.name}: {formatRupee(entry.value)}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full bg-slate-900/30 border border-electric-500/20 rounded-xl p-6 backdrop-blur-sm">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-50 flex items-center gap-2">
          📊 Revenue vs. Cost Trends
        </h2>
        <p className="text-slate-400 text-sm mt-2">
          Last 14 days of revenue and cost of goods sold
        </p>
      </div>

      <div className="overflow-x-auto">
        <ResponsiveContainer width="100%" height={350} minWidth={500}>
          <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.revenue} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS.revenue} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.cost} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS.cost} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
            <XAxis
              dataKey="date"
              stroke="#94a3b8"
              style={{
                fontSize: '12px',
              }}
            />
            <YAxis
              stroke="#94a3b8"
              style={{
                fontSize: '12px',
              }}
              tickFormatter={(value) => {
                if (value >= 10000) return `₹${(value / 1000).toFixed(0)}K`
                return `₹${value}`
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{
                paddingTop: '20px',
              }}
            />
            <Area
              type="monotone"
              dataKey="revenue"
              stroke={COLORS.revenue}
              name="Revenue"
              fillOpacity={1}
              fill="url(#colorRevenue)"
              isAnimationActive={true}
              animationDuration={800}
            />
            <Area
              type="monotone"
              dataKey="cost"
              stroke={COLORS.cost}
              name="Cost"
              fillOpacity={1}
              fill="url(#colorCost)"
              isAnimationActive={true}
              animationDuration={800}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-4 text-sm">
        <div className="bg-electric-500/10 border border-electric-500/30 rounded-lg p-3">
          <p className="text-slate-400">Avg Daily Revenue</p>
          <p className="text-electric-300 font-bold text-lg">
            {formatRupee(data.reduce((sum, d) => sum + d.revenue, 0) / data.length)}
          </p>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
          <p className="text-slate-400">Avg Daily Cost</p>
          <p className="text-red-300 font-bold text-lg">
            {formatRupee(data.reduce((sum, d) => sum + d.cost, 0) / data.length)}
          </p>
        </div>
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
          <p className="text-slate-400">Avg Daily Profit</p>
          <p className="text-green-300 font-bold text-lg">
            {formatRupee(
              data.reduce((sum, d) => sum + (d.revenue - d.cost), 0) / data.length
            )}
          </p>
        </div>
      </div>
    </div>
  )
}
