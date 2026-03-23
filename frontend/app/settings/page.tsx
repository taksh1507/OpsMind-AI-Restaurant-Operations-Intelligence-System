'use client'

import { Settings } from 'lucide-react'

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-electric-500/20 pb-6">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2 flex items-center gap-3">
          <Settings size={32} className="text-electric-400" />
          Settings
        </h1>
        <p className="text-slate-400">
          Manage your restaurant configuration and preferences
        </p>
      </div>

      {/* Settings Sections */}
      <div className="space-y-6">
        {/* Restaurant Info */}
        <div className="p-6 rounded-xl border border-electric-500/30 bg-slate-800/30 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-slate-50 mb-4">Restaurant Information</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Restaurant Name</label>
              <input
                type="text"
                defaultValue="La Bella Italia"
                className="w-full px-4 py-2 rounded-lg bg-slate-900/50 border border-slate-700 text-slate-50 focus:border-electric-500 focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Timezone</label>
              <select className="w-full px-4 py-2 rounded-lg bg-slate-900/50 border border-slate-700 text-slate-50 focus:border-electric-500 focus:outline-none transition-colors">
                <option>America/New_York (EST)</option>
                <option>America/Chicago (CST)</option>
                <option>America/Los_Angeles (PST)</option>
              </select>
            </div>
          </div>
        </div>

        {/* API Configuration */}
        <div className="p-6 rounded-xl border border-electric-500/30 bg-slate-800/30 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-slate-50 mb-4">AI Configuration</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-200 font-medium">Gemini AI Integration</p>
                <p className="text-slate-400 text-sm">AI insights and recommendations</p>
              </div>
              <div className="w-12 h-6 bg-electric-600 rounded-full flex items-center px-1">
                <div className="w-5 h-5 bg-white rounded-full ml-auto transition-all" />
              </div>
            </div>
            <div className="flex items-center justify-between pt-4 border-t border-slate-700">
              <div>
                <p className="text-slate-200 font-medium">Weather Context Awareness</p>
                <p className="text-slate-400 text-sm">Adjust recommendations based on weather</p>
              </div>
              <div className="w-12 h-6 bg-electric-600 rounded-full flex items-center px-1">
                <div className="w-5 h-5 bg-white rounded-full ml-auto transition-all" />
              </div>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="p-6 rounded-xl border border-red-500/30 bg-red-900/10 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-red-300 mb-4">Danger Zone</h2>
          <button className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors font-medium">
            Delete Account
          </button>
          <p className="text-red-300/70 text-sm mt-2">This action cannot be undone.</p>
        </div>
      </div>
    </div>
  )
}
