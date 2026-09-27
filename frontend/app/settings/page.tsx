'use client'

import { useEffect, useState } from 'react'
import useSWR from 'swr'
import { Settings as SettingsIcon, Save, Lock, Cpu, CloudSun, Sparkles, Store } from 'lucide-react'
import { useUserRole } from '@/hooks/useUserRole'
import { showToast } from '@/hooks/useWebSocket'
import { fetchSettings, updateSettings, extractApiError } from '@/lib/settings-api'
import type { Settings, UpdateSettingsInput } from '@/types/settings'
import AiUsageCard from './AiUsageCard'

const inputClass =
  'w-full px-4 py-2 rounded-[3px] bg-background border border-line text-foreground focus:border-accent focus:outline-none transition-colors'
const labelClass =
  'block text-sm font-display font-semibold tracking-wide text-cream-dim mb-2'

const TIMEZONES = [
  'America/New_York',
  'America/Chicago',
  'America/Los_Angeles',
  'Europe/London',
  'Asia/Kolkata',
  'Asia/Dubai',
  'UTC',
]

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`w-12 h-6 rounded-full flex items-center px-1 transition-colors flex-shrink-0 ${
        checked ? 'bg-accent' : 'bg-surface-2 border border-line'
      }`}
    >
      <span
        className={`w-4 h-4 bg-white rounded-full transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

export default function SettingsPage() {
  const { isOwner, loading: roleLoading } = useUserRole()

  // Only owners can read/write settings server-side, so only fetch for them.
  const { data, error, isLoading, mutate } = useSWR<Settings>(
    isOwner ? 'settings' : null,
    fetchSettings,
    { revalidateOnFocus: false },
  )

  const [form, setForm] = useState<UpdateSettingsInput>({})
  const [saving, setSaving] = useState(false)

  // Seed the editable form once settings load (and whenever they change).
  useEffect(() => {
    if (data) {
      setForm({
        restaurant_name: data.restaurant_name,
        timezone: data.timezone,
        ai_model: data.ai_model,
        ai_insights_enabled: data.ai_insights_enabled,
        weather_enabled: data.weather_enabled,
        default_city: data.default_city ?? '',
      })
    }
  }, [data])

  const set = <K extends keyof UpdateSettingsInput>(
    key: K,
    value: UpdateSettingsInput[K],
  ) => setForm((f) => ({ ...f, [key]: value }))

  const handleSave = async () => {
    if (!form.restaurant_name || !form.restaurant_name.trim()) {
      showToast('Restaurant name is required', 'error')
      return
    }
    setSaving(true)
    try {
      const updated = await updateSettings({
        ...form,
        restaurant_name: form.restaurant_name.trim(),
        // Send "" (not null) when blank: the API clears the city on empty
        // string but treats null as "leave unchanged".
        default_city: (form.default_city ?? '').trim(),
      })
      await mutate(updated, { revalidate: false })
      showToast('Settings saved', 'success')
    } catch (e) {
      showToast(extractApiError(e) || 'Failed to save settings', 'error')
    } finally {
      setSaving(false)
    }
  }

  const models = data?.available_models ?? []
  // Ensure the saved timezone is always selectable even if it's not in our list.
  const timezoneOptions =
    form.timezone && !TIMEZONES.includes(form.timezone)
      ? [form.timezone, ...TIMEZONES]
      : TIMEZONES

  if (roleLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-accent" />
      </div>
    )
  }

  const header = (
    <div className="border-b border-accent/20 pb-6">
      <h1 className="font-display text-4xl font-bold text-foreground mb-1 flex items-center gap-3">
        <SettingsIcon size={32} className="text-accent" />
        Settings
      </h1>
      <p className="text-cream-dim">
        Configure your restaurant&apos;s AI and operational preferences
      </p>
    </div>
  )

  if (!isOwner) {
    return (
      <div className="space-y-8">
        {header}
        <div className="flex items-center gap-2 text-sm text-cream-dim bg-surface-2 border border-line rounded-[3px] px-4 py-3">
          <Lock size={14} className="text-accent" />
          Only the owner can view and change settings.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {header}
      {error && (
        <p className="text-alert bg-alert/10 border border-alert/30 rounded-[3px] px-4 py-3">
          {extractApiError(error) || 'Failed to load settings. Please refresh to retry.'}
        </p>
      )}
      {(isLoading || !data) && !error && (
        <p className="text-cream-dim">Loading settings…</p>
      )}
      {data && (
        <div className="space-y-6">
          <section className="bg-surface border border-line rounded-[3px] p-6 space-y-5">
            <h2 className="font-display text-xl font-semibold text-foreground flex items-center gap-2">
              <Store size={18} className="text-accent" />
              Restaurant Information
            </h2>
            <div>
              <label className={labelClass}>Restaurant Name</label>
              <input
                type="text"
                className={inputClass}
                value={form.restaurant_name ?? ''}
                onChange={(e) => set('restaurant_name', e.target.value)}
                placeholder="e.g. The Copper Fork"
              />
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label className={labelClass}>Timezone</label>
                <select
                  className={inputClass}
                  value={form.timezone ?? ''}
                  onChange={(e) => set('timezone', e.target.value)}
                >
                  {timezoneOptions.map((tz) => (
                    <option key={tz} value={tz}>
                      {tz}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>Default City (weather)</label>
                <input
                  type="text"
                  className={inputClass}
                  value={form.default_city ?? ''}
                  onChange={(e) => set('default_city', e.target.value)}
                  placeholder="e.g. New York"
                />
              </div>
            </div>
          </section>
          <section className="bg-surface border border-line rounded-[3px] p-6 space-y-5">
            <h2 className="font-display text-xl font-semibold text-foreground flex items-center gap-2">
              <Cpu size={18} className="text-accent" />
              AI Configuration
            </h2>
            <div>
              <label className={labelClass}>AI Model</label>
              <select
                className={inputClass}
                value={form.ai_model ?? ''}
                onChange={(e) => set('ai_model', e.target.value)}
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
              {models.find((m) => m.id === form.ai_model)?.description && (
                <p className="text-xs text-cream-dim mt-2">
                  {models.find((m) => m.id === form.ai_model)?.description}
                </p>
              )}
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-line pt-4">
              <div className="flex items-start gap-3">
                <Sparkles size={18} className="text-accent mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-foreground">AI Insights</p>
                  <p className="text-xs text-cream-dim">
                    Generate AI-powered daily tips and analytics narratives.
                  </p>
                </div>
              </div>
              <Toggle
                checked={!!form.ai_insights_enabled}
                onChange={(v) => set('ai_insights_enabled', v)}
                label="Toggle AI insights"
              />
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-line pt-4">
              <div className="flex items-start gap-3">
                <CloudSun size={18} className="text-accent mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Weather Signals</p>
                  <p className="text-xs text-cream-dim">
                    Factor local weather into daily tips and demand forecasts.
                  </p>
                </div>
              </div>
              <Toggle
                checked={!!form.weather_enabled}
                onChange={(v) => set('weather_enabled', v)}
                label="Toggle weather signals"
              />
            </div>
          </section>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-[3px] bg-accent text-background font-display font-semibold tracking-wide hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save size={16} />
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}
      <AiUsageCard />
    </div>
  )

}

