'use client'

import { useEffect } from 'react'
import { X } from 'lucide-react'

interface ModalProps {
  open: boolean
  title: string
  onClose: () => void
  children: React.ReactNode
}

/** Generic centered modal with a scrim, close button, and Escape-to-close. */
export function Modal({ open, title, onClose, children }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} aria-hidden />
      <div className="relative w-full max-w-lg bg-surface border border-line rounded-[3px] ticket-perf shadow-xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-line">
          <h3 className="font-display text-lg font-bold tracking-wide text-foreground">
            {title}
          </h3>
          <button
            onClick={onClose}
            aria-label="Close"
            className="p-1 rounded-[3px] text-cream-dim hover:text-foreground hover:bg-surface-2 transition-colors"
          >
            <X size={18} />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  )
}
