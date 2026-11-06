'use client'
import useSWR from 'swr'
import { analyticsFetcher, type SalesSummary } from '@/lib/analytics-api'

export function useDashboardStats() {
  const { data, error, isLoading, mutate } = useSWR<SalesSummary, Error>(
    '/analytics/summary', analyticsFetcher, { refreshInterval: 60000, revalidateOnFocus: false })
  return { stats: data?.metrics, period: data?.period, isLoading, isError: !!error, error, mutate }
}
