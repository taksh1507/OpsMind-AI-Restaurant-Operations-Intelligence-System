// Analytics Types
export interface DashboardStats {
  total_revenue_usd: number
  total_revenue_inr: number
  profit_margin: number
  ai_confidence_score: number
  active_orders: number
  staff_efficiency: number
  system_alerts: number
  total_profit_usd: number
  total_profit_inr: number
  revenue_change: number
  profit_change: number
  confidence_change: number
}

export interface AnalyticsSummary {
  date: string
  stats: DashboardStats
  top_performers: Array<{
    name: string
    units_sold: number
    revenue: number
  }>
  underperformers: Array<{
    name: string
    units_sold: number
    revenue: number
  }>
}

// API Response Wrapper
export interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
}

// Error Response
export interface ApiError {
  success: false
  error: string
  details?: Record<string, unknown>
}
