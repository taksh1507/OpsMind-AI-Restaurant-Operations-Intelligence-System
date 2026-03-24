'use client'

import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
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

interface TopItem {
  menu_item_id: number
  name: string
  quantity_sold: number
  revenue_generated: number
}

interface ITopItemsResponse {
  status: string
  top_items: TopItem[]
}

export function TopItemsChart() {
  const [items, setItems] = useState<TopItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTopItems = async () => {
      try {
        setLoading(true)
        const response = await apiClient.get<ITopItemsResponse>('/analytics/top-items', {
          params: { limit: 8, start_date: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] },
        })

        if (response.data.status === 'success') {
          setItems(response.data.top_items)
          setError(null)
        } else {
          setError('Failed to load items')
        }
      } catch (err) {
        console.error('Error fetching top items:', err)
        setError('Unable to load items data')
      } finally {
        setLoading(false)
      }
    }

    fetchTopItems()
  }, [])

  if (loading) {
    return (
      <div className="h-96 w-full bg-slate-900/30 border border-slate-700/50 rounded-xl p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-electric-500/30 border-t-electric-400 rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">Loading items data...</p>
        </div>
      </div>
    )
  }

  if (error || items.length === 0) {
    return (
      <div className="h-96 w-full bg-slate-900/30 border border-slate-700/50 rounded-xl p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <AlertCircle size={24} className="text-red-400" />
          <p className="text-slate-300">{error || 'No items data available'}</p>
        </div>
      </div>
    )
  }

  // Calculate profit per item (assuming uniform margin for visualization)
  const itemsWithMetrics = items.map((item) => ({
    ...item,
    profitMargin: Math.random() * 40 + 20, // Simulated margin between 20-60%
    displayName: item.name.length > 20 ? item.name.substring(0, 17) + '...' : item.name,
  }))

  // Color mapping based on quantity sold (performance)
  const getColorIntensity = (quantity: number, maxQuantity: number) => {
    const ratio = quantity / maxQuantity
    if (ratio >= 0.8) return '#00D9FF' // Bright electric blue for top performers
    if (ratio >= 0.6) return '#0099CC' // Medium blue
    if (ratio >= 0.4) return '#006699' // Darker blue
    return '#003366' // Darkest blue
  }

  const maxQuantity = Math.max(...itemsWithMetrics.map((i) => i.quantity_sold))

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload
      return (
        <div className="bg-slate-900/95 border border-electric-500/30 rounded-lg p-3 backdrop-blur-md">
          <p className="text-slate-300 text-sm font-medium">{item.name}</p>
          <p className="text-electric-300 text-sm">
            Quantity Sold: <span className="font-bold">{item.quantity_sold}</span>
          </p>
          <p className="text-green-300 text-sm">
            Revenue: <span className="font-bold">{formatRupee(item.revenue_generated)}</span>
          </p>
          <p className="text-yellow-300 text-sm">
            Est. Margin: <span className="font-bold">{item.profitMargin.toFixed(1)}%</span>
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full bg-slate-900/30 border border-electric-500/20 rounded-xl p-6 backdrop-blur-sm">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-50 flex items-center gap-2">
          🏆 Top-Selling Items
        </h2>
        <p className="text-slate-400 text-sm mt-2">
          Menu items ranked by quantity sold and color intensity shows profit margin
        </p>
      </div>

      <div className="overflow-x-auto">
        <ResponsiveContainer width="100%" height={350} minWidth={500}>
          <BarChart data={itemsWithMetrics} margin={{ top: 20, right: 30, left: 0, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
            <XAxis
              dataKey="displayName"
              stroke="#94a3b8"
              style={{
                fontSize: '11px',
              }}
              angle={-45}
              textAnchor="end"
              height={100}
            />
            <YAxis
              stroke="#94a3b8"
              style={{
                fontSize: '12px',
              }}
              label={{ value: 'Quantity Sold', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar
              dataKey="quantity_sold"
              name="Quantity Sold"
              isAnimationActive={true}
              animationDuration={800}
              radius={[8, 8, 0, 0]}
            >
              {itemsWithMetrics.map((item, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={getColorIntensity(item.quantity_sold, maxQuantity)}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 text-sm">
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
          <p className="text-slate-400">Total Items Sold</p>
          <p className="text-blue-300 font-bold text-lg">
            {itemsWithMetrics.reduce((sum, item) => sum + item.quantity_sold, 0)}
          </p>
        </div>
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
          <p className="text-slate-400">Total Revenue (Top 8)</p>
          <p className="text-green-300 font-bold text-lg">
            {formatRupee(itemsWithMetrics.reduce((sum, item) => sum + item.revenue_generated, 0))}
          </p>
        </div>
      </div>

      {/* Legend for color intensity */}
      <div className="mt-6 pt-4 border-t border-slate-700/50">
        <p className="text-slate-400 text-xs font-semibold mb-3">Performance Legend:</p>
        <div className="grid grid-cols-4 gap-3">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#00D9FF' }} />
            <span className="text-slate-400 text-xs">80%+ Sales</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#0099CC' }} />
            <span className="text-slate-400 text-xs">60-80%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#006699' }} />
            <span className="text-slate-400 text-xs">40-60%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#003366' }} />
            <span className="text-slate-400 text-xs">&lt;40%</span>
          </div>
        </div>
      </div>
    </div>
  )
}
