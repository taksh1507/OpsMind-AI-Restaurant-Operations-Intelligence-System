'use client'

import React, { useCallback, useEffect, useState } from 'react'
import { Command, defaultFilter } from 'cmdk'
import { Search, BarChart3, Zap, Moon, Sun, Menu, LayoutDashboard, UtensilsCrossed, Users } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useSearch } from '@/hooks/useSearch'
import { useUserRole } from '@/hooks/useUserRole'
import { showToast } from '@/hooks/useWebSocket'

export function CommandMenu() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const { results: searchResults, loading, error, search, clear } = useSearch()
  const { canManage } = useUserRole()
  const [isDark, setIsDark] = useState(true)
  const router = useRouter()
  const close = useCallback(() => { clear(); setQuery(''); setOpen(false) }, [clear])

  // Keyboard shortcut handler
  useEffect(() => {
    let awaitingNavigation = false
    let shortcutTimer: ReturnType<typeof setTimeout> | undefined
    const openSearch = () => setOpen(true)
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (open) close()
        else setOpen(true)
        return
      }

      // Close on Escape
      if (e.key === 'Escape') {
        close()
        return
      }
      const target = e.target
      if (open || (target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)))) return
      if (awaitingNavigation) {
        awaitingNavigation = false
        clearTimeout(shortcutTimer)
        const routes: Record<string, string> = { d: '/', m: '/menu', ...(canManage ? { a: '/insights', s: '/sales' } : {}) }
        if (routes[e.key]) { e.preventDefault(); router.push(routes[e.key]) }
      } else if (e.key === 'g') {
        awaitingNavigation = true
        shortcutTimer = setTimeout(() => { awaitingNavigation = false }, 2000)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('opsmind:open-search', openSearch)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('opsmind:open-search', openSearch)
      clearTimeout(shortcutTimer)
    }
  }, [open, router, close, canManage])

  // Search handler
  const handleSearch = (value: string) => {
    setQuery(value)
    search(value)
  }

  const handleThemeToggle = () => {
    setIsDark(!isDark)
    document.documentElement.classList.toggle('dark')
    close()
  }

  const handleNavigation = (path: string) => {
    router.push(path)
    close()
  }

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 "
        onClick={close}
      />

      {/* Command Menu */}
      <div role="dialog" aria-modal="true" aria-label="Global search" className="relative w-full max-w-2xl mx-4 shadow-2xl rounded-[3px] border border-line bg-surface">
        <Command filter={(value, input) => value.startsWith("search-result:") ? 1 : defaultFilter(value, input)} className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-cream-dim [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group]:overflow-hidden [&_[cmdk-group]]:px-1.5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5">
          <div className="flex items-center border-b border-line px-4 py-3">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <Command.Input
              autoFocus
              placeholder={canManage ? 'Search menu, staff, or navigate...' : 'Search menu or navigate...'}
              value={query}
              maxLength={100}
              className="flex h-11 w-full rounded-[3px] bg-transparent py-3 text-sm outline-none placeholder:text-cream-dim text-foreground"
              onValueChange={handleSearch}
            />
          </div>

          <Command.List className="max-h-96 overflow-y-auto">
            {!loading && !error && <Command.Empty className="px-4 py-8 text-center text-sm text-cream-dim">
              No results found.
            </Command.Empty>}

            {error && <p role="alert" className="px-4 py-2 text-sm text-red-400">{error}</p>}
            {loading && <p role="status" className="px-4 py-2 text-sm text-cream-dim">Searching…</p>}
            {/* Search Results */}
            {searchResults.length > 0 && (
              <Command.Group heading="Search Results">
                {searchResults.map((result) => (
                  <Command.Item
                    key={`${result.category}:${result.id}`}
                    value={`search-result:${result.category}:${result.id}:${result.name}`}
                    onSelect={() => {
                      if (result.category === 'menu') {
                        handleNavigation(`/menu?id=${result.id}`)
                      } else if (result.category === 'staff') {
                        showToast(`${result.name}: ${result.description ?? 'Staff member'}`)
                        close()
                      } else {
                        handleNavigation(`/menu?category=${result.id}`)
                      }
                    }}
                    className="cursor-pointer hover:bg-surface-2"
                  >
                    <div>
                      {result.category === 'menu' && <UtensilsCrossed className="mr-2 h-4 w-4" />}
                      {result.category === 'staff' && <Users className="mr-2 h-4 w-4" />}
                      {result.category === 'category' && <Menu className="mr-2 h-4 w-4" />}
                    </div>
                    <div className="flex flex-col">
                      <span className="font-medium text-foreground">{result.name}</span>
                      {result.description && (
                        <span className="text-xs text-cream-dim">{result.description}</span>
                      )}
                    </div>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Navigation Actions */}
            <Command.Group heading="Navigate">
              <Command.Item
                onSelect={() => handleNavigation('/')}
                className="cursor-pointer hover:bg-surface-2"
              >
                <LayoutDashboard className="mr-2 h-4 w-4" />
                <div className="flex flex-col">
                  <span className="text-foreground">Dashboard</span>
                  <span className="text-xs text-cream-dim">G then D</span>
                </div>
              </Command.Item>

              <Command.Item
                onSelect={() => handleNavigation('/menu')}
                className="cursor-pointer hover:bg-surface-2"
              >
                <UtensilsCrossed className="mr-2 h-4 w-4" />
                <div className="flex flex-col">
                  <span className="text-foreground">Menu</span>
                  <span className="text-xs text-cream-dim">G then M</span>
                </div>
              </Command.Item>

              {canManage && <Command.Item
                onSelect={() => handleNavigation('/insights')}
                className="cursor-pointer hover:bg-surface-2"
              >
                <BarChart3 className="mr-2 h-4 w-4" />
                <div className="flex flex-col">
                  <span className="text-foreground">Analytics</span>
                  <span className="text-xs text-cream-dim">G then A</span>
                </div>
              </Command.Item>}

              {canManage && <Command.Item
                onSelect={() => handleNavigation('/sales')}
                className="cursor-pointer hover:bg-surface-2"
              >
                <Zap className="mr-2 h-4 w-4" />
                <div className="flex flex-col">
                  <span className="text-foreground">Sales</span>
                  <span className="text-xs text-cream-dim">G then S</span>
                </div>
              </Command.Item>}
            </Command.Group>

            {/* Theme */}
            <Command.Group heading="Theme">
              <Command.Item
                onSelect={handleThemeToggle}
                className="cursor-pointer hover:bg-surface-2"
              >
                {isDark ? (
                  <>
                    <Sun className="mr-2 h-4 w-4" />
                    <span className="text-foreground">Light Mode</span>
                  </>
                ) : (
                  <>
                    <Moon className="mr-2 h-4 w-4" />
                    <span className="text-foreground">Dark Mode</span>
                  </>
                )}
              </Command.Item>
            </Command.Group>
          </Command.List>

          <div className="border-t border-line px-4 py-2 text-right text-xs text-cream-dim">
            <div className="flex items-center justify-end gap-2">
              <kbd className="rounded px-2 py-1 bg-surface-2 text-cream-dim text-xs font-semibold">
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
