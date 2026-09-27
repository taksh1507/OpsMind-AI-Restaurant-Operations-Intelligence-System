// Thin API layer for owner-managed tenant settings. Wraps the OWNER-gated
// endpoints in app/api/settings.py (GET/PUT /settings).

import apiClient from './api-client'
import type { Settings, UpdateSettingsInput } from '@/types/settings'

export async function fetchSettings(): Promise<Settings> {
  const { data } = await apiClient.get<Settings>('/settings')
  return data
}

export async function updateSettings(
  input: UpdateSettingsInput,
): Promise<Settings> {
  const { data } = await apiClient.put<Settings>('/settings', input)
  return data
}

// Re-export so callers get one import site for menu-style error extraction.
export { extractApiError } from './menu-api'
