'use client'

import { useEffect, useState } from 'react'
import { Modal } from '@/components/ui'
import { extractApiError } from '@/lib/menu-api'
import type { Category, CategoryInput } from '@/types/menu'

const inputClass =
  'w-full px-4 py-2 rounded-[3px] bg-background border border-line text-foreground focus:border-accent focus:outline-none transition-colors'
const labelClass =
  'block text-sm font-display font-semibold tracking-wide text-cream-dim mb-2'

interface Props {
  open: boolean
  initial?: Category | null
  onClose: () => void
  onSubmit: (input: CategoryInput) => Promise<void>
}

export function CategoryFormModal({ open, initial, onClose, onSubmit }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setName(initial?.name ?? '')
      setDescription(initial?.description ?? '')
      setIsActive(initial?.is_active ?? true)
      setError(null)
    }
  }, [open, initial])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Category name is required')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim() || null,
        is_active: isActive,
      })
      onClose()
    } catch (err) {
      setError(extractApiError(err) || 'Failed to save category')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} title={initial ? 'Edit Category' : 'Add Category'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <p className="text-sm text-alert bg-alert/10 border border-alert/30 rounded-[3px] px-3 py-2">
            {error}
          </p>
        )}
        <div>
          <label className={labelClass}>Name</label>
          <input
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Appetizers"
            autoFocus
          />
        </div>
        <div>
          <label className={labelClass}>Description (optional)</label>
          <textarea
            className={inputClass}
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="accent-accent"
          />
          Active (visible on the menu)
        </label>
        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-[3px] border border-line text-cream-dim hover:text-foreground hover:bg-surface-2 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 rounded-[3px] bg-accent text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
