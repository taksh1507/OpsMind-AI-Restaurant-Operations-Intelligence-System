'use client'

import { useState } from 'react'
import useSWR from 'swr'
import apiClient from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'
import { showToast } from '@/hooks/useWebSocket'
import { DashboardSkeleton } from '@/components/ui'
import {
  TrendingUp,
  LineChart,
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Calendar,
  Zap,
  BarChart3,
  RefreshCw
} from 'lucide-react'

// SWR fetcher
const fetcher = async (url: string) => {
  const res = await apiClient.get(url)
  return res.data
}

export default function ModelPerformancePage() {
  const { isAuthenticated } = useAuth()
  const { data, error, isLoading, mutate } = useSWR('/analytics/model-performance', fetcher, {
    revalidateOnFocus: false,
    shouldRetryOnError: false
  })
  const [isRetraining, setIsRetraining] = useState(false)

  // Trigger retraining
  const handleRetrain = async () => {
    setIsRetraining(true)
    showToast('Starting background model retraining and backtesting...', 'info')
    try {
      await apiClient.post('/ml/retrain?model_type=all')
      showToast('Models successfully retrained and backtesting report updated!', 'success')
      mutate() // Refresh data
    } catch (err: any) {
      console.error(err)
      const errMsg = err.response?.data?.detail || 'Failed to trigger model retraining.'
      showToast(errMsg, 'error')
    } finally {
      setIsRetraining(false)
    }
  }

  // Auth checking lifecycle
  if (isAuthenticated === null) {
    return <DashboardSkeleton />
  }

  // Loading skeleton
  if (isLoading) {
    return <DashboardSkeleton />
  }

  // Handle 404 or missing report error
  const is404 = error?.response?.status === 404
  if (error && !is404) {
    return (
      <div className="space-y-8">
        <div className="border-b border-electric-500/20 pb-6">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2 flex items-center gap-3">
            <LineChart size={32} className="text-electric-400" />
            Model Performance
          </h1>
          <p className="text-slate-400">View forecasting evaluation and model calibration metrics</p>
        </div>
        <div className="p-6 rounded-xl border border-red-500/30 bg-red-900/10">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-red-400 flex-shrink-0 mt-1" size={20} />
            <div>
              <h3 className="text-red-300 font-semibold mb-1">Failed to Load Performance Metrics</h3>
              <p className="text-red-300/70 text-sm">
                {error.message || 'An error occurred while loading performance metrics.'}
              </p>
              <button
                onClick={() => mutate()}
                className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors text-sm font-medium"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (is404 || !data) {
    return (
      <div className="space-y-8">
        <div className="border-b border-electric-500/20 pb-6">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2 flex items-center gap-3">
            <LineChart size={32} className="text-electric-400" />
            Model Performance
          </h1>
          <p className="text-slate-400">View forecasting evaluation and model calibration metrics</p>
        </div>
        <div className="p-8 rounded-xl border border-electric-500/30 bg-slate-900/40 backdrop-blur-md text-center max-w-2xl mx-auto space-y-6">
          <div className="mx-auto w-16 h-16 rounded-full bg-electric-950 flex items-center justify-center border border-electric-500/30">
            <Zap className="text-electric-400 animate-pulse" size={28} />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-slate-100">No Backtest Metrics Available</h2>
            <p className="text-slate-400 text-sm">
              Your forecasting model has not been trained yet, or has no historical performance logs.
              Run retraining to build your machine learning pipelines and calculate baseline benchmarking.
            </p>
          </div>
          <button
            onClick={handleRetrain}
            disabled={isRetraining}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-gradient-to-r from-electric-600 to-electric-500 hover:from-electric-500 hover:to-electric-400 text-white font-medium transition-all shadow-glow-electric disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRetraining ? (
              <>
                <RefreshCw className="animate-spin" size={20} />
                Retraining Models...
              </>
            ) : (
              <>
                <Play size={20} />
                Retrain Models & Run Backtest
              </>
            )}
          </button>
        </div>
      </div>
    )
  }

  // Calculate lift percentage
  const lift = data.naive_mae > 0 ? ((data.naive_mae - data.xgboost_mae) / data.naive_mae) * 100 : 0
  const isLiftPositive = lift >= 0
  const isStable = data.stability_ratio < 0.20

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-electric-500/20 pb-6">
        <div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2 flex items-center gap-3">
            <LineChart size={32} className="text-electric-400" />
            Model Performance
          </h1>
          <p className="text-slate-400">View forecasting evaluation and model calibration metrics</p>
        </div>
        <div>
          <button
            onClick={handleRetrain}
            disabled={isRetraining}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-electric-600 border border-electric-500/50 hover:bg-electric-500 text-white transition-all shadow-glow-electric disabled:opacity-50 disabled:cursor-not-allowed text-sm font-semibold"
          >
            {isRetraining ? (
              <>
                <RefreshCw className="animate-spin" size={16} />
                Retraining...
              </>
            ) : (
              <>
                <RefreshCw size={16} />
                Retrain Models
              </>
            )}
          </button>
        </div>
      </div>

      {/* Summary Metrics Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* MAE Lift Card */}
        <div className="p-6 rounded-xl border border-electric-500/20 bg-slate-900/40 backdrop-blur-sm relative overflow-hidden group hover:border-electric-500/40 transition-all">
          <div className="absolute top-0 right-0 p-4 opacity-10 text-electric-400 group-hover:scale-110 transition-transform">
            <TrendingUp size={64} />
          </div>
          <p className="text-sm font-medium text-slate-400 uppercase tracking-wider">Overall MAE Lift</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-3xl font-extrabold ${isLiftPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isLiftPositive ? '+' : ''}{lift.toFixed(1)}%
            </span>
            <span className="text-xs text-slate-500">improvement</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            XGBoost Forecaster average MAE of <span className="text-slate-300 font-semibold">{data.xgboost_mae}</span> vs. Naive baseline of <span className="text-slate-300 font-semibold">{data.naive_mae}</span>.
          </p>
        </div>

        {/* Stability Check Card */}
        <div className="p-6 rounded-xl border border-electric-500/20 bg-slate-900/40 backdrop-blur-sm relative overflow-hidden group hover:border-electric-500/40 transition-all">
          <div className="absolute top-0 right-0 p-4 opacity-10 text-electric-400 group-hover:scale-110 transition-transform">
            <Zap size={64} />
          </div>
          <p className="text-sm font-medium text-slate-400 uppercase tracking-wider">Stability Check</p>
          <div className="mt-2 flex items-center gap-2">
            {isStable ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-green-500/20 text-green-300 border border-green-500/30">
                <CheckCircle2 size={14} /> PASSED
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-500/20 text-red-300 border border-red-500/30">
                <XCircle size={14} /> FAILED
              </span>
            )}
            <span className="text-2xl font-bold text-slate-200">{(data.stability_ratio * 100).toFixed(1)}%</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Stability ratio measures MAE variance. Current ratio is <span className="text-slate-300 font-semibold">{(data.stability_ratio).toFixed(4)}</span> (target threshold &lt; 0.2000).
          </p>
        </div>

        {/* RMSE Performance Card */}
        <div className="p-6 rounded-xl border border-electric-500/20 bg-slate-900/40 backdrop-blur-sm relative overflow-hidden group hover:border-electric-500/40 transition-all">
          <div className="absolute top-0 right-0 p-4 opacity-10 text-electric-400 group-hover:scale-110 transition-transform">
            <BarChart3 size={64} />
          </div>
          <p className="text-sm font-medium text-slate-400 uppercase tracking-wider">Model RMSE</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-electric-300">{data.xgboost_rmse}</span>
            <span className="text-xs text-slate-500">avg error scale</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Measures penalty on large outliers. XGBoost RMSE is <span className="text-slate-300 font-semibold">{data.xgboost_rmse}</span>, indicating highly consistent predictions.
          </p>
        </div>
      </div>

      {/* Week-by-Week Backtest Report Table */}
      <div className="border border-electric-500/20 rounded-xl bg-slate-900/40 backdrop-blur-sm overflow-hidden">
        <div className="p-6 border-b border-electric-500/10 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Calendar size={20} className="text-electric-400" />
            Weekly Backtest Performance Logs
          </h2>
          <span className="text-xs text-slate-400 font-mono">Last 8 Windows Evaluated</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-950/40 border-b border-electric-500/10 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <th className="px-6 py-4">Week</th>
                <th className="px-6 py-4">Date Range</th>
                <th className="px-6 py-4 text-right">Naive MAE</th>
                <th className="px-6 py-4 text-right">XGB MAE</th>
                <th className="px-6 py-4 text-right">XGB RMSE</th>
                <th className="px-6 py-4 text-right">Performance Lift</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-electric-500/10 text-sm text-slate-300">
              {data.weeks.map((week: any) => {
                const weekLift = week.naive_mae > 0 ? ((week.naive_mae - week.xgb_mae) / week.naive_mae) * 100 : 0
                const isWeekLiftPositive = weekLift >= 0
                return (
                  <tr key={week.week_idx} className="hover:bg-slate-800/20 transition-colors">
                    <td className="px-6 py-4 font-semibold text-electric-400">Week {week.week_idx}</td>
                    <td className="px-6 py-4 text-slate-400">{week.start_date} to {week.end_date}</td>
                    <td className="px-6 py-4 text-right font-mono">₹{week.naive_mae.toFixed(2)}</td>
                    <td className="px-6 py-4 text-right font-mono text-slate-100 font-semibold">₹{week.xgb_mae.toFixed(2)}</td>
                    <td className="px-6 py-4 text-right font-mono text-slate-400">₹{week.xgb_rmse.toFixed(2)}</td>
                    <td className={`px-6 py-4 text-right font-mono font-semibold ${isWeekLiftPositive ? 'text-green-400' : 'text-red-400'}`}>
                      {isWeekLiftPositive ? '+' : ''}{weekLift.toFixed(1)}%
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
