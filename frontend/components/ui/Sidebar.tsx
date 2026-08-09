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
  Lock,
  LineChart
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
  { label: 'Model Performance', href: '/model-performance', icon: <LineChart size={20} />, requiredRoles: [UserRole.OWNER, UserRole.MANAGER] },
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
      <aside className="fixed left-0 top-0 h-screen w-20 md:w-64 bg-slate-900 border-r border-slate-700 hidden md:flex md:flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-electric-500"></div>
      </aside>
    )
  }

  return (
    <>
      {/* Mobile Menu Button */}
      <div className="fixed top-4 left-4 z-50 md:hidden">
        <button
          onClick={toggleMobile}
          className="p-2 rounded-[3px] bg-slate-800 border border-slate-700 hover:border-electric-700 transition-colors"
          aria-label="Toggle menu"
        >
          {isMobileOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        className={`
          fixed left-0 top-0 h-screen bg-slate-900 border-r border-slate-700
          transition-all duration-300 z-40 overflow-hidden
          relative
          before:content-[''] before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[2px]
          before:bg-[repeating-linear-gradient(to_bottom,var(--accent)_0_6px,transparent_6px_12px)] before:opacity-50
          ${isExpanded ? 'w-64' : 'w-20'}
          hidden md:flex md:flex-col
          ${isMobileOpen ? 'w-64 flex flex-col' : ''}
        `}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-700 flex items-center justify-between">
          {isExpanded && (
            <div>
              <h1 className="font-display text-xl font-bold tracking-wide text-slate-50">
                Ops<span className="text-electric-500">Mind</span>
              </h1>
              <p className="text-[10px] font-medium uppercase tracking-[0.15em] text-slate-400 mt-0.5">
                Kitchen Intelligence
              </p>
            </div>
          )}
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-[3px] hover:bg-slate-800 transition-colors hidden md:block"
            aria-label="Toggle sidebar"
          >
            {isExpanded ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
          </button>
        </div>

        {/* Day 25: Role Badge */}
        {isExpanded && userRole && (
          <div className="px-4 py-2 mx-4 mt-3 rounded-[3px] bg-slate-800 border border-slate-700">
            <div className="flex items-center gap-2">
              <Lock size={13} className="text-electric-500" />
              <span className="font-display text-xs font-semibold uppercase tracking-wide text-slate-200">{userRole}</span>
            </div>
          </div>
        )}

        {/* Navigation - Day 25: Only show items user has role for */}
        <nav className="flex-1 p-3 space-y-1 mt-2">
          {visibleNavItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`
                relative flex items-center gap-3 px-4 py-2.5 rounded-[3px]
                transition-colors duration-150
                hover:bg-slate-800 text-slate-300 hover:text-slate-50
                group
                ${!isExpanded && 'justify-center px-0'}
              `}
              title={!isExpanded ? item.label : undefined}
            >
              <span className="flex-shrink-0 text-electric-500">
                {item.icon}
              </span>
              {isExpanded && (
                <span className="font-display text-[15px] font-semibold tracking-wide">{item.label}</span>
              )}
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
        <div className="p-4 border-t border-slate-700 space-y-2">
          <div
            className={`
              flex items-center gap-3 px-3 py-1
              ${isExpanded ? 'text-xs text-slate-400' : 'justify-center'}
            `}
          >
            {isExpanded && (
              <div>
                <p className="font-display text-sm font-semibold tracking-wide text-slate-200">Tandoor House</p>
                <p className="text-slate-500 text-[11px]">Owner &middot; JWT verified</p>
              </div>
            )}
          </div>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className={`
              w-full flex items-center gap-3 px-4 py-2.5 rounded-[3px]
              transition-colors duration-150
              hover:bg-alert/10 hover:text-alert
              text-slate-300
              group
              ${!isExpanded && 'justify-center px-0'}
            `}
            title={!isExpanded ? 'Logout' : undefined}
          >
            <span className="flex-shrink-0 text-slate-400 group-hover:text-alert">
              <LogOut size={18} />
            </span>
            {isExpanded && <span className="font-display text-[15px] font-semibold tracking-wide">Logout</span>}
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
