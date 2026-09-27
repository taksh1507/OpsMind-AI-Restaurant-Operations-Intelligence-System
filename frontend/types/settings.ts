// Types for owner-managed tenant settings (AI model, feature toggles, timezone,
// restaurant name). Mirrors the SettingsResponse / UpdateSettingsRequest schemas
// in app/models/schemas.py.

export interface ModelOption {
  id: string
  label: string
  description: string
}

export interface Settings {
  restaurant_name: string
  timezone: string
  ai_model: string
  ai_insights_enabled: boolean
  weather_enabled: boolean
  default_city: string | null
  available_models: ModelOption[]
}

export interface UpdateSettingsInput {
  restaurant_name?: string
  timezone?: string
  ai_model?: string
  ai_insights_enabled?: boolean
  weather_enabled?: boolean
  default_city?: string | null
}
