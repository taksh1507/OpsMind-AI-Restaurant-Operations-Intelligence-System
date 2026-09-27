// Types for the owner-facing AI usage view (Phase 4). Mirrors the response of
// get_usage_summary in app/services/ai_usage_service.py (GET /ai-usage).

export interface AiUsageFeature {
  feature: string
  total_tokens: number
  calls: number
}

export interface AiUsage {
  tenant_id: number
  period_start: string
  period_label: string
  // When false, usage is metered but never blocked (cap disabled on the server).
  enforced: boolean
  monthly_token_cap: number | null
  tokens_used: number
  input_tokens: number
  output_tokens: number
  tokens_remaining: number | null
  percent_used: number | null
  total_calls: number
  by_feature: AiUsageFeature[]
}
