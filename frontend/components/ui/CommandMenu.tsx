'use client'

import React, { useEffect, useState } from 'react'
import { Command } from 'cmdk'
import { Search, BarChart3, Zap, Moon, Sun, Menu, LayoutDashboard, UtensilsCrossed, Users } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface SearchResult {
  id: string
  name: string
  category: 'menu' | 'category' | 'staff'
  description?: string
}

export function CommandMenu() {
  const [open, setOpen] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [isDark, setIsDark] = useState(true)
  const router = useRouter()

  // Keyboard shortcut handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((prev) => !prev)
      }

      // Close on Escape
      if (e.key === 'Escape') {
        setOpen(false)
      }

      // Keyboard shortcuts for navigation (G prefix)
      if (e.key === 'g' && !open) {
        // Allow 'g' to trigger next shortcut
        const handleNextKey = (nextEvent: KeyboardEvent) => {
          if (nextEvent.key === 'd') {
            nextEvent.preventDefault()
            router.push('/dashboard')
            document.removeEventListener('keydown', handleNextKey)
          } else if (nextEvent.key === 'm') {
            nextEvent.preventDefault()
            router.push('/menu')
            document.removeEventListener('keydown', handleNextKey)
          } else if (nextEvent.key === 'a') {
            nextEvent.preventDefault()
            router.push('/insights')
            document.removeEventListener('keydown', handleNextKey)
          } else if (nextEvent.key === 's') {
            nextEvent.preventDefault()
            router.push('/sales')
            document.removeEventListener('keydown', handleNextKey)
          } else if (nextEvent.key !== 'g') {
            document.removeEventListener('keydown', handleNextKey)
          }
        }
        document.addEventListener('keydown', handleNextKey)
        setTimeout(() => {
          document.removeEventListener('keydown', handleNextKey)
        }, 2000)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, router])

  // Search handler
  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([])
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
      if (response.ok) {
        const data = await response.json()
        setSearchResults(data.results || [])
      }
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleThemeToggle = () => {
    setIsDark(!isDark)
    document.documentElement.classList.toggle('dark')
    setOpen(false)
  }

  const handleNavigation = (path: string) => {
    router.push(path)
    setOpen(false)
  }

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* Command Menu */}
      <div className="relative w-full max-w-2xl mx-4 shadow-2xl rounded-lg border border-slate-700 bg-slate-900">
        <Command className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-slate-500 [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group]:overflow-hidden [&_[cmdk-group]]:px-1.5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5">
          <div className="flex items-center border-b border-slate-700 px-4 py-3">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <Command.Input
              placeholder="Search menu, staff, or navigate..."
              className="flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-slate-500 text-slate-100"
              onValueChange={handleSearch}
            />
          </div>

          <Command.List className="max-h-96 overflow-y-auto">
            <Command.Empty className="px-4 py-8 text-center text-sm text-slate-400">
              {loading ? 'Searching...' : 'No results found.'}
            </Command.Empty>

            {/* Search Results */}
            {searchResults.length > 0 && (
              <Command.Group heading="Search Results">
                {searchResults.map((result) => (
                  <Command.Item
                    key={result.id}
                    value={result.id}
                    onSelect={() => {
                      if (result.category === 'menu') {
                        handleNavigation(`/menu?id=${result.id}`)
                      } else if (result.category === 'staff') {
                        handleNavigation(`/settings`)
                      } else {
                        handleNavigation(`/menu?category=${result.id}`)
                      }
                    }}
                    className="cursor-pointer hover:bg-slate-800"
                  >
                    <div>
                      {result.category === 'menu' && <UtensilsCrossed className="mr-2 h-4 w-4" />}
                      {result.category === 'staff' && <Users className="mr-2 h-4 w-4" />}
                      {result.category === 'category' && <Menu className="mr-2 h-4 w-4" />}
                    </div>
                    <div className="flex flex-col">
                      <span className="font-medium text-slate-100">{result.name}</span>
                      {result.description && (
                        <span className="text-xs text-slate-400">{result.description}</span>
                      )}
                    </div>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Navigation Actions */}
            <Command.Group heading="Navigate">
              <Command.Item
                onSelect={() => handleNavigation('/dashboard')}
                className="cursor-pointer hover:bg-slate-800"
              >
                <LayoutDashboard className="mr-2 h-4 w-4" />
                <div className="flex flex-col">
                  <span className="text-slate-100">Dashboard</span>
                  <span className="text-xs text-slate-500">G then D</span>
                </div>
              </Command.Item>

              <Command.Item
                onSelect={() => handleNavigation('/menu')}
                className="cursor-pointer hover:bg-slate-800"
              >
                <UtensilsCrossed className="mr-2 h-4 w-4" />
                <div className="flex flex-col">
                  <span className="text-slate-100">Menu</span>
                  <span className="text-xs text-slate-500">G then M</span>
                </div>
              </Command.Item>

              <Command.Item
                onSelect={() => handleNavigation('/insights')}
                className="cursor-pointer hover:bg-slate-800"
              >
                <BarChart3 className="mr-2 h-4 w-4" />
                <div className="flex flex-col">
                  <span className="text-slate-100">Analytics</span>
                  <span className="text-xs text-slate-500">G then A</span>
                </div>
              </Command.Item>

              <Command.Item
                onSelect={() => handleNavigation('/sales')}
                className="cursor-pointer hover:bg-slate-800"
              >
                <Zap className="mr-2 h-4 w-4" />
                <div className="flex flex-col">
                  <span className="text-slate-100">Sales</span>
                  <span className="text-xs text-slate-500">G then S</span>
                </div>
              </Command.Item>
            </Command.Group>

            {/* Theme */}
            <Command.Group heading="Theme">
              <Command.Item
                onSelect={handleThemeToggle}
                className="cursor-pointer hover:bg-slate-800"
              >
                {isDark ? (
                  <>
                    <Sun className="mr-2 h-4 w-4" />
                    <span className="text-slate-100">Light Mode</span>
                  </>
                ) : (
                  <>
                    <Moon className="mr-2 h-4 w-4" />
                    <span className="text-slate-100">Dark Mode</span>
                  </>
                )}
              </Command.Item>
            </Command.Group>
          </Command.List>

          <div className="border-t border-slate-700 px-4 py-2 text-right text-xs text-slate-500">
            <div className="flex items-center justify-end gap-2">
              <kbd className="rounded px-2 py-1 bg-slate-800 text-slate-300 text-xs font-semibold">
                ESC
              </kbd>
              <span>to close</span>
            </div>
          </div>
        </Command>
      </div>
    </div>
  )
}
