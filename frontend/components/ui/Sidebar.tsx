'use client'

import Link from 'next/link'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  UtensilsCrossed,
  TrendingUp,
  Sparkles,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  LogOut,
  Lock
} from 'lucide-react'

// Day 25: Role-Based Access Control
enum UserRole {
  OWNER = 'owner',
  MANAGER = 'manager',
  STAFF = 'staff'
}

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
  requiredRoles?: UserRole[]  // If not specified, visible to all
}

// Navigation items with role requirements
const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/', icon: <LayoutDashboard size={20} /> },
  { label: 'Menu', href: '/menu', icon: <UtensilsCrossed size={20} /> },
  { label: 'Sales', href: '/sales', icon: <TrendingUp size={20} />, requiredRoles: [UserRole.OWNER, UserRole.MANAGER] },
  { label: 'AI Insights', href: '/insights', icon: <Sparkles size={20} />, requiredRoles: [UserRole.OWNER, UserRole.MANAGER] },  // Financial data - hide from STAFF
  { label: 'Settings', href: '/settings', icon: <Settings size={20} />, requiredRoles: [UserRole.OWNER, UserRole.MANAGER] },  // Admin functions
]

export function Sidebar() {
  const [isExpanded, setIsExpanded] = useState(true)
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const [userRole, setUserRole] = useState<UserRole | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  // Day 25: Extract user role from JWT token on mount
  useEffect(() => {
    const extractUserRole = () => {
      try {
        const token = localStorage.getItem('access_token')
        if (!token) {
          setUserRole(UserRole.STAFF)  // Default to STAFF if no token
          setLoading(false)
          return
        }

        // Decode JWT (format: header.payload.signature)
        const parts = token.split('.')
        if (parts.length !== 3) {
          setUserRole(UserRole.STAFF)
          setLoading(false)
          return
        }

        // Decode the payload (middle part)
        const payload = JSON.parse(atob(parts[1]))
        const role = payload.role as UserRole || UserRole.STAFF

        setUserRole(role)
      } catch (error) {
        console.error('Error extracting user role:', error)
        setUserRole(UserRole.STAFF)  // Safe default
      } finally {
        setLoading(false)
      }
    }

    extractUserRole()
  }, [])

  // Day 25: Filter nav items based on user role
  const visibleNavItems = navItems.filter((item) => {
    // If no role requirement, show to everyone
    if (!item.requiredRoles) return true
    // Show if user has one of the required roles
    return userRole && item.requiredRoles.includes(userRole)
  })

  const toggleSidebar = () => {
    setIsExpanded(!isExpanded)
  }

  const toggleMobile = () => {
    setIsMobileOpen(!isMobileOpen)
  }

  const handleLogout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token')
      localStorage.removeItem('token_type')
      router.push('/login')
    }
  }

  if (loading) {
    // Show loading state while role is being loaded
    return (
      <aside className="fixed left-0 top-0 h-screen w-20 md:w-64 bg-slate-900/80 backdrop-blur-md border-r border-electric-glow hidden md:flex md:flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-electric-400"></div>
      </aside>
    )
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

        {/* Day 25: Role Badge */}
        {isExpanded && userRole && (
          <div className="px-4 py-2 mx-2 rounded-lg bg-slate-800/50 border border-electric-glow/30">
            <div className="flex items-center gap-2">
              <Lock size={14} className="text-electric-400" />
              <span className="text-xs font-semibold text-electric-300 capitalize">{userRole}</span>
            </div>
          </div>
        )}

        {/* Navigation - Day 25: Only show items user has role for */}
        <nav className="flex-1 p-4 space-y-2">
          {visibleNavItems.map((item) => (
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

          {/* Day 25: Show message if user has no visible items (shouldn't happen, but good UX) */}
          {visibleNavItems.length === 0 && (
            <div className="px-4 py-3 text-xs text-slate-500 text-center">
              No accessible items
            </div>
          )}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-electric-glow/30 space-y-2">
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

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className={`
              w-full flex items-center gap-3 px-4 py-3 rounded-lg
              border border-transparent transition-all duration-200
              hover:border-red-500/30 hover:bg-red-900/20 hover:text-red-300
              text-slate-300
              group
              ${!isExpanded && 'justify-center px-0'}
            `}
            title={!isExpanded ? 'Logout' : undefined}
          >
            <span className="flex-shrink-0 text-slate-400 group-hover:text-red-300">
              <LogOut size={20} />
            </span>
            {isExpanded && <span className="text-sm font-medium">Logout</span>}
          </button>
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
