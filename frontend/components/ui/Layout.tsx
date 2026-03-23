'use client'

import React from 'react'
import { Sidebar } from './Sidebar'

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen bg-slate-950 dark">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden ml-0 md:ml-64">
        {/* Header Bar */}
        <header className="h-16 border-b border-electric-glow/20 bg-slate-900/40 backdrop-blur-sm flex items-center px-6 sticky top-0 z-20">
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-slate-100">Dashboard</h2>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-slate-400">
              Welcome back, Owner
            </div>
          </div>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-auto">
          <div className="p-6 md:p-8">
            {children}
          </div>
        </div>
      </main>
    </div>
  )
}
