'use client'

import useSWR from 'swr'
import apiClient from '@/lib/api-client'
import { DashboardStats, ApiResponse } from '@/types/api'

interface DashboardStatsResponse extends ApiResponse<DashboardStats> {}

// Create fetcher for SWR
const fetcher = async (url: string): Promise<DashboardStatsResponse> => {
  const response = await apiClient.get(url)
  return response.data
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
  const { data, error, isLoading, mutate } = useSWR<DashboardStatsResponse>(
    '/analytics/summary', // Endpoint from Day 6
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
    stats: data?.data,
    isLoading,
    isError: !!error,
    error,
    mutate,
  }
}
