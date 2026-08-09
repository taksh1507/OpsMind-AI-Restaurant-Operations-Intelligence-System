'use client'

import React from 'react'
import { Sidebar } from './Sidebar'
import { CommandMenu } from './CommandMenu'
import { ToastContainer } from './ToastContainer'
import { useWebSocket } from '@/hooks/useWebSocket'

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  // Initialize WebSocket connection for real-time events
  useWebSocket({
    onNewSale: (data) => {
      console.log('New sale received:', data);
      // Sales data is already handled in hook with toast/sound
    },
    onNewOrder: (data) => {
      console.log('New order received:', data);
    },
    onTableReady: (data) => {
      console.log('Table ready:', data);
    },
    autoReconnect: true,
    reconnectDelay: 3000,
  });
  return (
    <div className="flex h-screen bg-slate-950 dark">
      {/* Command Menu Overlay */}
      <CommandMenu />

      {/* Sidebar */}
      <Sidebar />

      {/* Real-time Toast Notifications */}
      <ToastContainer />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden ml-0 md:ml-64">
        {/* Header Bar */}
        <header className="h-16 border-b border-slate-700 bg-slate-900 flex items-center px-6 sticky top-0 z-20">
          <div className="flex-1">
            <h2 className="font-display text-xl font-semibold tracking-wide text-slate-50">Tonight&rsquo;s Pass</h2>
          </div>
          <div className="flex items-center gap-4">
            {/* Keyboard Shortcut Hint */}
            <button
              onClick={() => {}}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-[3px] bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-300 transition-colors"
              aria-label="Open command menu with Ctrl+K"
              title="Press Ctrl+K or Cmd+K to open the command menu"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span className="hidden sm:inline">Quick search...</span>
              <kbd className="px-2 py-0.5 bg-slate-900 rounded-[2px] text-slate-400 text-xs ml-auto">⌘K</kbd>
            </button>

            <div className="font-data text-xs text-electric-500 border border-electric-700 rounded-[2px] px-3 py-1.5">
              SAT &middot; AUG 09 &middot; 21:14
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
