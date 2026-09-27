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
  revenue: '#C77D3F', // Copper (accent)
  cost: '#C1442E', // Alert red
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
      <div className="h-80 w-full bg-surface/30 border border-line/50 rounded-[3px] p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-line border-t-electric-400 rounded-full animate-spin" />
          <p className="text-cream-dim text-sm">Loading chart data...</p>
        </div>
      </div>
    )
  }

  if (error || data.length === 0) {
    return (
      <div className="h-80 w-full bg-surface/30 border border-line/50 rounded-[3px] p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <AlertCircle size={24} className="text-red-400" />
          <p className="text-cream-dim">{error || 'No data available'}</p>
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
        <div className="bg-surface/95 border border-line rounded-[3px] p-3 ">
          <p className="text-cream-dim text-sm font-display font-semibold tracking-wide">{payload[0].payload.date}</p>
          {payload.map((entry: any, index: number) => (
            <p
              key={index}
              className="text-sm font-display font-semibold tracking-wide"
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
    <div className="w-full bg-surface/30 border border-accent/20 rounded-[3px] p-6 ">
      <div className="mb-6">
        <div className="flex items-center gap-2.5">
          <span className="w-[3px] h-[18px] bg-accent rounded-[2px]" />
          <h2 className="font-display text-lg font-bold tracking-wide text-foreground">Revenue vs. Cost Trends</h2>
        </div>
        <p className="text-cream-dim text-sm mt-2">
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
            <CartesianGrid strokeDasharray="3 3" stroke="#3A322B" opacity={0.5} />
            <XAxis
              dataKey="date"
              stroke="#B8A88C"
              style={{
                fontSize: '12px',
              }}
            />
            <YAxis
              stroke="#B8A88C"
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
        <div className="bg-accent/10 border border-line rounded-[3px] p-3">
          <p className="text-cream-dim">Avg Daily Revenue</p>
          <p className="text-electric-300 font-bold text-lg">
            {formatRupee(data.reduce((sum, d) => sum + d.revenue, 0) / data.length)}
          </p>
        </div>
        <div className="bg-alert/10 border border-alert/30 rounded-[3px] p-3">
          <p className="text-cream-dim">Avg Daily Cost</p>
          <p className="text-alert font-bold text-lg">
            {formatRupee(data.reduce((sum, d) => sum + d.cost, 0) / data.length)}
          </p>
        </div>
        <div className="bg-success/10 border border-success/30 rounded-[3px] p-3">
          <p className="text-cream-dim">Avg Daily Profit</p>
          <p className="text-success font-bold text-lg">
            {formatRupee(
              data.reduce((sum, d) => sum + (d.revenue - d.cost), 0) / data.length
            )}
          </p>
        </div>
      </div>
    </div>
  )
}
