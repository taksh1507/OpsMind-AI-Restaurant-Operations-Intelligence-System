'use client'

import React from 'react'
import { Sidebar } from './Sidebar'
import { CommandMenu } from './CommandMenu'
import { ToastContainer } from './ToastContainer'
import { useWebSocket } from '@/hooks/useWebSocket'
import { usePathname } from 'next/navigation'

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  const pathname = usePathname()
  const isAuthPage = pathname === '/login' || pathname === '/register'

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

  // Render raw children for auth pages (no sidebar, no header)
  if (isAuthPage) {
    return <>{children}</>
  }

  return (
    <div className="flex h-screen bg-background text-foreground dark">
      {/* Command Menu Overlay */}
      <CommandMenu />

      {/* Sidebar */}
      <Sidebar />

      {/* Real-time Toast Notifications */}
      <ToastContainer />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden w-full md:pl-64">
        {/* Header Bar */}
        <header className="h-16 border-b border-line bg-surface flex items-center px-6 sticky top-0 z-20">
          <div className="flex-1">
            <h2 className="font-display text-xl font-semibold tracking-wide text-foreground">Tonight&rsquo;s Pass</h2>
          </div>
          <div className="flex items-center gap-4">
            {/* Keyboard Shortcut Hint */}
            <button
              onClick={() => {}}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-[3px] bg-surface-2 hover:bg-surface border border-line text-xs text-cream-dim transition-colors"
              aria-label="Open command menu with Ctrl+K"
              title="Press Ctrl+K or Cmd+K to open the command menu"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span className="hidden sm:inline">Quick search...</span>
              <kbd className="px-2 py-0.5 bg-background rounded-[2px] text-cream-dim text-xs ml-auto">⌘K</kbd>
            </button>

            <div className="font-data text-xs text-accent border border-accent/40 rounded-[2px] px-3 py-1.5">
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
