import { useEffect, useState } from 'react'

interface KeyboardShortcut {
  keys: string[]
  description: string
  action: () => void
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const keysMatch = shortcut.keys.some((key) => event.key.toLowerCase() === key.toLowerCase())
        const ctrlMatch = shortcut.ctrlKey ? event.ctrlKey || event.metaKey : true
        const shiftMatch = shortcut.shiftKey ? event.shiftKey : true
        const altMatch = shortcut.altKey ? event.altKey : true

        if (keysMatch && ctrlMatch && shiftMatch && altMatch) {
          event.preventDefault()
          shortcut.action()
          break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [shortcuts])
}

export const COMMON_SHORTCUTS = {
  DASHBOARD: { keys: ['g', 'd'], description: 'Go to Dashboard' },
  MENU: { keys: ['g', 'm'], description: 'Go to Menu' },
  ANALYTICS: { keys: ['g', 'a'], description: 'Go to Analytics' },
  SALES: { keys: ['g', 's'], description: 'Go to Sales' },
  SETTINGS: { keys: ['g', 't'], description: 'Go to Settings' },
  SEARCH: { keys: ['k'], description: 'Open Search', ctrlKey: true },
}
