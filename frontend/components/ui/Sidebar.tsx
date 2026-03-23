'use client'

import Link from 'next/link'
import { useState } from 'react'
import {
  LayoutDashboard,
  UtensilsCrossed,
  TrendingUp,
  Sparkles,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X
} from 'lucide-react'

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/', icon: <LayoutDashboard size={20} /> },
  { label: 'Menu', href: '/menu', icon: <UtensilsCrossed size={20} /> },
  { label: 'Sales', href: '/sales', icon: <TrendingUp size={20} /> },
  { label: 'AI Insights', href: '/insights', icon: <Sparkles size={20} /> },
  { label: 'Settings', href: '/settings', icon: <Settings size={20} /> },
]

export function Sidebar() {
  const [isExpanded, setIsExpanded] = useState(true)
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  const toggleSidebar = () => {
    setIsExpanded(!isExpanded)
  }

  const toggleMobile = () => {
    setIsMobileOpen(!isMobileOpen)
  }

  return (
    <>
      {/* Mobile Menu Button */}
      <div className="fixed top-4 left-4 z-50 md:hidden">
        <button
          onClick={toggleMobile}
          className="p-2 rounded-lg bg-slate-800 border border-electric-glow hover:bg-slate-700 transition-colors"
          aria-label="Toggle menu"
        >
          {isMobileOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        className={`
          fixed left-0 top-0 h-screen bg-slate-900/80 backdrop-blur-md border-r border-electric-glow
          transition-all duration-300 z-40 overflow-hidden
          ${isExpanded ? 'w-64' : 'w-20'}
          hidden md:flex md:flex-col
          ${isMobileOpen ? 'w-64 flex flex-col' : ''}
        `}
      >
        {/* Header */}
        <div className="p-4 border-b border-electric-glow/30 flex items-center justify-between">
          {isExpanded && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-electric-500 to-electric-700 flex items-center justify-center">
                <span className="text-white text-sm font-bold">OM</span>
              </div>
              <h1 className="text-lg font-bold text-electric-400">OpsMind</h1>
            </div>
          )}
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors hidden md:block"
            aria-label="Toggle sidebar"
          >
            {isExpanded ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg
                border border-transparent transition-all duration-200
                hover:border-electric-500 hover:bg-slate-800/50 hover:shadow-glow-electric
                text-slate-300 hover:text-electric-300
                group
                ${!isExpanded && 'justify-center px-0'}
              `}
              title={!isExpanded ? item.label : undefined}
            >
              <span className="flex-shrink-0 text-electric-400 group-hover:text-electric-300">
                {item.icon}
              </span>
              {isExpanded && <span className="text-sm font-medium">{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-electric-glow/30">
          <div
            className={`
              flex items-center gap-3 px-3 py-2 rounded-lg
              ${isExpanded ? 'text-xs text-slate-400' : 'justify-center'}
            `}
          >
            {isExpanded && (
              <div>
                <p className="font-semibold text-slate-200">Restaurant AI</p>
                <p className="text-slate-500">v0.1.0</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}
    </>
  )
}
