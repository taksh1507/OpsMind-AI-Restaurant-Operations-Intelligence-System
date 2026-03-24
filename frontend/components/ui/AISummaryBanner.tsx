'use client'

import { useEffect, useState } from 'react'
import { Sparkles, AlertTriangle, TrendingUp } from 'lucide-react'
import apiClient from '@/lib/api-client'

interface AIBriefing {
  health_assessment?: string
  star_dishes?: string[]
  pricing_opportunities?: string[]
  cost_optimization_opportunities?: string[]
  top_recommendation?: string
  executive_summary?: string
}

interface IAPISummaryResponse {
  status: string
  briefing: AIBriefing
  cache_hit?: boolean
}

export function AISummaryBanner() {
  const [summary, setSummary] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [cacheHit, setCacheHit] = useState(false)

  useEffect(() => {
    const fetchAISummary = async () => {
      try {
        setLoading(true)
        const response = await apiClient.get<IAPISummaryResponse>('/analytics/ai-briefing')

        if (response.data.status === 'success') {
          const briefing = response.data.briefing
          
          // Generate summary from briefing data
          let summaryText = ""
          
          if (briefing.top_recommendation) {
            summaryText = briefing.top_recommendation
          } else if (briefing.executive_summary) {
            summaryText = briefing.executive_summary
          } else if (briefing.health_assessment) {
            summaryText = briefing.health_assessment
          } else {
            // Fallback summary
            summaryText = "Your restaurant is performing well. Focus on optimizing your top-selling items and exploring pricing opportunities."
          }
          
          setSummary(summaryText)
          setCacheHit(response.data.cache_hit || false)
          setError(null)
        } else {
          setError('Could not generate AI summary')
        }
      } catch (err) {
        console.error('Error fetching AI summary:', err)
        setError('Unable to generate AI insights')
      } finally {
        setLoading(false)
      }
    }

    fetchAISummary()
  }, [])

  if (error) {
    return (
      <div className="w-full bg-red-900/20 border border-red-500/30 rounded-xl p-6 backdrop-blur-sm">
        <div className="flex items-start gap-4">
          <AlertTriangle size={24} className="text-red-400 mt-1 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-red-300 mb-2">AI Analysis Unavailable</h3>
            <p className="text-red-200 text-sm">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full bg-gradient-to-r from-electric-900/40 to-electric-800/20 border border-electric-500/30 rounded-xl p-6 backdrop-blur-sm overflow-hidden">
      {/* Animated background pulse */}
      <div className="absolute inset-0 -z-10">
        <div
          className="absolute inset-0 bg-gradient-to-r from-electric-500/0 via-electric-500/10 to-electric-500/0 animate-pulse"
          style={{
            animation: 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
          }}
        />
      </div>

      <div className="flex items-start gap-4">
        {/* AI Icon with pulse animation */}
        <div className="relative flex-shrink-0">
          <div
            className="absolute inset-0 bg-electric-400/20 rounded-lg blur-lg animate-pulse"
            style={{
              animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            }}
          />
          <div className="relative bg-gradient-to-br from-electric-500 to-electric-600 rounded-lg p-3">
            {loading ? (
              <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Sparkles size={24} className="text-white" />
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-bold text-electric-200">AI Strategic Insight</h3>
            {cacheHit && (
              <span className="px-2 py-1 bg-blue-500/20 border border-blue-500/30 rounded text-xs text-blue-300 font-medium">
                Cached
              </span>
            )}
          </div>

          {loading ? (
            <div className="space-y-2">
              <div className="h-4 bg-slate-700/30 rounded animate-pulse w-3/4" />
              <div className="h-4 bg-slate-700/30 rounded animate-pulse w-1/2" />
            </div>
          ) : summary ? (
            <p className="text-electric-100 text-base leading-relaxed font-medium">
              {summary}
            </p>
          ) : (
            <p className="text-slate-400 text-sm italic">
              No AI insights available at this time.
            </p>
          )}

          {/* Call-to-action hint */}
          <div className="mt-4 flex items-center gap-2 text-xs text-electric-300">
            <TrendingUp size={14} />
            <span>Powered by Gemini 1.5 Flash • Real-time analysis</span>
          </div>
        </div>
      </div>

      {/* Decorative corner accent */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-electric-500/5 rounded-bl-3xl -z-10" />
    </div>
  )
}
