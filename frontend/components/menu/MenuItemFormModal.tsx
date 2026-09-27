'use client'

import { useEffect, useState } from 'react'
import { Modal } from '@/components/ui'
import { extractApiError } from '@/lib/menu-api'
import type { Category, MenuItem, MenuItemInput } from '@/types/menu'

const inputClass =
  'w-full px-4 py-2 rounded-[3px] bg-background border border-line text-foreground focus:border-accent focus:outline-none transition-colors'
const labelClass =
  'block text-sm font-display font-semibold tracking-wide text-cream-dim mb-2'

interface Props {
  open: boolean
  initial?: MenuItem | null
  categories: Category[]
  defaultCategoryId?: number | null
  onClose: () => void
  onSubmit: (input: MenuItemInput) => Promise<void>
}

export function MenuItemFormModal({
  open,
  initial,
  categories,
  defaultCategoryId,
  onClose,
  onSubmit,
}: Props) {
  const [categoryId, setCategoryId] = useState<number | ''>('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [costPrice, setCostPrice] = useState('')
  const [isAvailable, setIsAvailable] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setCategoryId(initial?.category_id ?? defaultCategoryId ?? categories[0]?.id ?? '')
    setName(initial?.name ?? '')
    setDescription(initial?.description ?? '')
    setPrice(initial ? String(Number(initial.price)) : '')
    setCostPrice(initial ? String(Number(initial.cost_price)) : '')
    setIsAvailable(initial?.is_available ?? true)
    setError(null)
  }, [open, initial, defaultCategoryId, categories])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (categoryId === '') {
      setError('Select a category')
      return
    }
    if (!name.trim()) {
      setError('Item name is required')
      return
    }
    const p = Number(price)
    const c = Number(costPrice)
    if (!Number.isFinite(p) || p <= 0) {
      setError('Price must be greater than 0')
      return
    }
    if (!Number.isFinite(c) || c < 0) {
      setError('Cost price must be 0 or more')
      return
    }
    if (p <= c) {
      setError('Price must be greater than cost price')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onSubmit({
        category_id: categoryId,
        name: name.trim(),
        description: description.trim() || null,
        price: p,
        cost_price: c,
        is_available: isAvailable,
      })
      onClose()
    } catch (err) {
      setError(extractApiError(err) || 'Failed to save item')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} title={initial ? 'Edit Item' : 'Add Item'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <p className="text-sm text-alert bg-alert/10 border border-alert/30 rounded-[3px] px-3 py-2">
            {error}
          </p>
        )}
        <div>
          <label className={labelClass}>Category</label>
          <select
            className={inputClass}
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : '')}
          >
            {categories.length === 0 && <option value="">No categories yet</option>}
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass}>Name</label>
          <input
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Margherita Pizza"
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
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Price</label>
            <input
              className={inputClass}
              type="number"
              step="0.01"
              min="0"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
            />
          </div>
          <div>
            <label className={labelClass}>Cost price</label>
            <input
              className={inputClass}
              type="number"
              step="0.01"
              min="0"
              value={costPrice}
              onChange={(e) => setCostPrice(e.target.value)}
              placeholder="0.00"
            />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={isAvailable}
            onChange={(e) => setIsAvailable(e.target.checked)}
            className="accent-accent"
          />
          Available for sale
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
            disabled={saving || categories.length === 0}
            className="px-4 py-2 rounded-[3px] bg-accent text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
