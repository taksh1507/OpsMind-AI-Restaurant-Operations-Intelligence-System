'use client'

import useSWR from 'swr'
import { Gauge, RefreshCw } from 'lucide-react'
import { fetchAiUsage } from '@/lib/ai-usage-api'
import { extractApiError } from '@/lib/settings-api'
import type { AiUsage } from '@/types/ai-usage'

// Friendly names for the internal feature keys recorded server-side.
const FEATURE_LABELS: Record<string, string> = {
  daily_tip: 'Daily tip',
  strategy_briefing: 'Strategic briefing',
  margin_analysis: 'Margin analysis',
  review_response: 'Review responses',
  labor_efficiency: 'Labor efficiency',
  revenue_forecast: 'Revenue forecast',
}

const nf = new Intl.NumberFormat()

function labelFor(key: string): string {
  return FEATURE_LABELS[key] ?? key.replace(/_/g, ' ')
}

export default function AiUsageCard() {
  const { data, error, isLoading, mutate, isValidating } = useSWR<AiUsage>(
    'ai-usage',
    fetchAiUsage,
    { revalidateOnFocus: false },
  )

  const pct = data?.percent_used ?? 0
  const barWidth = Math.min(100, Math.max(0, pct))
  const nearLimit = !!data?.enforced && pct >= 90

  return (
    <section className="bg-surface border border-line rounded-[3px] p-6 space-y-5">
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-display text-xl font-semibold text-foreground flex items-center gap-2">
          <Gauge size={18} className="text-accent" />
          AI Usage{data?.period_label ? ` — ${data.period_label}` : ''}
        </h2>
        <button
          type="button"
          onClick={() => mutate()}
          disabled={isValidating}
          className="inline-flex items-center gap-1.5 text-xs text-cream-dim hover:text-foreground transition-colors disabled:opacity-50"
          aria-label="Refresh AI usage"
        >
          <RefreshCw size={13} className={isValidating ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {error && (
        <p className="text-alert bg-alert/10 border border-alert/30 rounded-[3px] px-4 py-3 text-sm">
          {extractApiError(error) || 'Failed to load AI usage.'}
        </p>
      )}
      {isLoading && !data && !error && (
        <p className="text-cream-dim text-sm">Loading usage…</p>
      )}

      {data && (
        <div className="space-y-5">
          {data.enforced ? (
            <div className="space-y-2">
              <div className="flex items-end justify-between gap-4">
                <p className="text-sm text-cream-dim">
                  <span className="text-2xl font-display font-bold text-foreground">
                    {nf.format(data.tokens_used)}
                  </span>{' '}
                  / {nf.format(data.monthly_token_cap ?? 0)} tokens
                </p>
                <p className={`text-sm font-semibold ${nearLimit ? 'text-alert' : 'text-accent'}`}>
                  {pct}% used
                </p>
              </div>
              <div className="h-2.5 w-full rounded-full bg-surface-2 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${nearLimit ? 'bg-alert' : 'bg-accent'}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
              <p className="text-xs text-cream-dim">
                {nf.format(Math.max(0, data.tokens_remaining ?? 0))} tokens remaining · resets at the
                start of next month{nearLimit ? ' · approaching your monthly limit' : ''}
              </p>
            </div>
          ) : (
            <p className="text-sm text-cream-dim">
              <span className="text-2xl font-display font-bold text-foreground">
                {nf.format(data.tokens_used)}
              </span>{' '}
              tokens used this month. No monthly limit is set for this deployment.
            </p>
          )}

          <div className="grid grid-cols-3 gap-3 border-t border-line pt-4 text-center">
            <div>
              <p className="text-lg font-display font-bold text-foreground">{nf.format(data.total_calls)}</p>
              <p className="text-xs text-cream-dim">AI calls</p>
            </div>
            <div>
              <p className="text-lg font-display font-bold text-foreground">{nf.format(data.input_tokens)}</p>
              <p className="text-xs text-cream-dim">Input tokens</p>
            </div>
            <div>
              <p className="text-lg font-display font-bold text-foreground">{nf.format(data.output_tokens)}</p>
              <p className="text-xs text-cream-dim">Output tokens</p>
            </div>
          </div>

          {data.by_feature.length > 0 && (
            <div className="border-t border-line pt-4 space-y-2">
              <p className="text-sm font-semibold text-foreground">By feature</p>
              <ul className="space-y-1.5">
                {data.by_feature.map((f) => (
                  <li key={f.feature} className="flex items-center justify-between text-sm">
                    <span className="text-cream-dim">
                      {labelFor(f.feature)}{' '}
                      <span className="text-xs opacity-70">({nf.format(f.calls)} calls)</span>
                    </span>
                    <span className="text-foreground">{nf.format(f.total_tokens)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.total_calls === 0 && (
            <p className="text-xs text-cream-dim border-t border-line pt-4">
              No AI features have run yet this month. Try the daily tip or a briefing to see usage here.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
