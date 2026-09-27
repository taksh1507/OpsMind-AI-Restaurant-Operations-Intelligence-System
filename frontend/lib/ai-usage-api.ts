// Thin API layer for the owner-facing AI usage view. Wraps the OWNER-gated
// GET /ai-usage endpoint (app/api/ai_usage.py).

import apiClient from './api-client'
import type { AiUsage } from '@/types/ai-usage'

export async function fetchAiUsage(): Promise<AiUsage> {
  const { data } = await apiClient.get<AiUsage>('/ai-usage')
  return data
}
