'use client'

import { Settings } from 'lucide-react'

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-accent/20 pb-6">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2 flex items-center gap-3">
          <Settings size={32} className="text-accent" />
          Settings
        </h1>
        <p className="text-cream-dim">
          Manage your restaurant configuration and preferences
        </p>
      </div>

      {/* Settings Sections */}
      <div className="space-y-6">
        {/* Restaurant Info */}
        <div className="p-6 rounded-xl border border-accent/30 bg-surface-2/30 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-foreground mb-4">Restaurant Information</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-cream-dim mb-2">Restaurant Name</label>
              <input
                type="text"
                defaultValue="La Bella Italia"
                className="w-full px-4 py-2 rounded-lg bg-surface/50 border border-line text-foreground focus:border-accent focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-cream-dim mb-2">Timezone</label>
              <select className="w-full px-4 py-2 rounded-lg bg-surface/50 border border-line text-foreground focus:border-accent focus:outline-none transition-colors">
                <option>America/New_York (EST)</option>
                <option>America/Chicago (CST)</option>
                <option>America/Los_Angeles (PST)</option>
              </select>
            </div>
          </div>
        </div>

        {/* API Configuration */}
        <div className="p-6 rounded-xl border border-accent/30 bg-surface-2/30 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-foreground mb-4">AI Configuration</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-foreground font-medium">Gemini AI Integration</p>
                <p className="text-cream-dim text-sm">AI insights and recommendations</p>
              </div>
              <div className="w-12 h-6 bg-electric-600 rounded-full flex items-center px-1">
                <div className="w-5 h-5 bg-white rounded-full ml-auto transition-all" />
              </div>
            </div>
            <div className="flex items-center justify-between pt-4 border-t border-line">
              <div>
                <p className="text-foreground font-medium">Weather Context Awareness</p>
                <p className="text-cream-dim text-sm">Adjust recommendations based on weather</p>
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
