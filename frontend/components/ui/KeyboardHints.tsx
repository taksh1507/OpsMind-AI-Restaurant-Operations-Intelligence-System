'use client'

import React from 'react'

interface KeyboardHintProps {
  keys: string[]
  description: string
  className?: string
}

export function KeyboardHint({ keys, description, className = '' }: KeyboardHintProps) {
  return (
    <div className={`flex items-center gap-2 text-xs text-cream-dim ${className}`}>
      <div className="flex items-center gap-1">
        {keys.map((key, idx) => (
          <React.Fragment key={idx}>
            {idx > 0 && <span className="text-cream-dim">+</span>}
            <kbd className="px-2 py-1 rounded bg-surface-2 text-cream-dim font-semibold text-xs border border-line">
              {key.length === 1 ? key.toUpperCase() : key}
            </kbd>
          </React.Fragment>
        ))}
      </div>
      <span>{description}</span>
    </div>
  )
}

export function KeyboardShortcutsPanel() {
  const shortcuts = [
    { keys: ['⌘', 'K'], description: 'Open command menu', group: 'Global' },
    { keys: ['G', 'D'], description: 'Go to Dashboard', group: 'Navigation' },
    { keys: ['G', 'M'], description: 'Go to Menu', group: 'Navigation' },
    { keys: ['G', 'A'], description: 'Go to Analytics', group: 'Navigation' },
    { keys: ['G', 'S'], description: 'Go to Sales', group: 'Navigation' },
    { keys: ['G', 'T'], description: 'Go to Settings', group: 'Navigation' },
    { keys: ['Esc'], description: 'Close menus/dialogs', group: 'UI' },
    { keys: ['Tab'], description: 'Navigate elements', group: 'UI' },
    { keys: ['Enter'], description: 'Activate button/link', group: 'UI' },
  ]

  const groups = Array.from(new Set(shortcuts.map((s) => s.group)))

  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <div key={group}>
          <h3 className="font-display text-xs font-semibold tracking-wide uppercase text-cream-dim mb-2">{group}</h3>
          <div className="space-y-2">
            {shortcuts
              .filter((s) => s.group === group)
              .map((shortcut, idx) => (
                <div key={idx} className="flex items-center justify-between px-3 py-2 bg-surface rounded-[3px] border border-line">
                  <span className="text-xs text-cream-dim">{shortcut.description}</span>
                  <div className="flex items-center gap-0.5">
                    {shortcut.keys.map((key, keyIdx) => (
                      <React.Fragment key={keyIdx}>
                        {keyIdx > 0 && <span className="mx-1 text-cream-dim/50">+</span>}
                        <kbd className="px-2 py-1 rounded-[2px] bg-background text-cream-dim text-xs font-mono border border-line">
                          {key}
                        </kbd>
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  )
}
