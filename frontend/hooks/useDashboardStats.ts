'use client'

import useSWR from 'swr'
import apiClient from '@/lib/api-client'
import { DashboardStats } from '@/types/api'

interface AnalyticsMetrics {
  total_revenue_usd: number
  total_revenue_inr: number
  total_profit_usd: number
  total_profit_inr: number
  profit_margin_percent: number
  cost_of_goods_sold_usd: number
  cost_of_goods_sold_inr: number
  transaction_count: number
  total_items_sold: number
}

interface AnalyticsApiResponse {
  status: string
  tenant_id: number
  period: {
    start_date: string
    end_date: string
  }
  metrics: AnalyticsMetrics
  top_selling_items: Array<any>
  message: string
}

// Create fetcher for SWR
const fetcher = async (url: string): Promise<DashboardStats> => {
  const response = await apiClient.get<AnalyticsApiResponse>(url)
  const metrics = response.data.metrics
  
  // Map API response to DashboardStats interface
  return {
    total_revenue_usd: metrics.total_revenue_usd,
    total_revenue_inr: metrics.total_revenue_inr,
    total_profit_usd: metrics.total_profit_usd,
    total_profit_inr: metrics.total_profit_inr,
    profit_margin: metrics.profit_margin_percent,
    ai_confidence_score: 85, // Placeholder - can be enhanced with real data
    active_orders: response.data.metrics.transaction_count,
    staff_efficiency: 88, // Placeholder
    system_alerts: 0,
    revenue_change: 12.5, // Placeholder for trend
    profit_change: 8.3, // Placeholder for trend
    confidence_change: 2.1, // Placeholder for trend
  }
}

export interface UseDashboardStatsReturn {
  stats: DashboardStats | undefined
  isLoading: boolean
  isError: boolean
  error: Error | undefined
  mutate: () => Promise<any>
}

/**
 * Hook to fetch and cache dashboard statistics from the backend
 * Uses SWR for automatic caching and revalidation
 * @returns Dashboard stats, loading state, and error state
 */
export function useDashboardStats(): UseDashboardStatsReturn {
  const { data, error, isLoading, mutate } = useSWR<DashboardStats>(
    '/analytics/summary', // Endpoint from Day 18
    fetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: 60000, // Cache for 1 minute
      focusThrottleInterval: 300000, // Revalidate after 5 minutes
      onError: (err) => {
        console.error('Failed to fetch dashboard stats:', err)
      },
    }
  )

  return {
    stats: data,
    isLoading,
    isError: !!error,
    error,
    mutate,
  }
}

