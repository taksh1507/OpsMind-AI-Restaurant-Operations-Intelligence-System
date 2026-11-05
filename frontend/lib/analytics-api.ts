import apiClient from './api-client'

export interface SalesSummary {
  currency: 'INR'
  period: { start_date: string; end_date: string }
  metrics: {
    total_revenue_inr: number
    total_profit_inr: number
    cost_of_goods_sold_inr: number
    profit_margin_percent: number
    transaction_count: number
    total_items_sold: number
    revenue_change: number | null
    profit_change: number | null
  }
}
export const analyticsFetcher = async <T,>(url: string): Promise<T> => (await apiClient.get<T>(url)).data
