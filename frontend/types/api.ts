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
