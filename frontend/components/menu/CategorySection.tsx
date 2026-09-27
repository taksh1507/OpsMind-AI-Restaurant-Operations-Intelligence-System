'use client'

import { Pencil, Trash2, Plus, Eye, EyeOff } from 'lucide-react'
import type { Category, MenuItem } from '@/types/menu'

const money = (v: number | string) => `$${Number(v).toFixed(2)}`
const marginPct = (price: number | string, cost: number | string) => {
  const p = Number(price)
  const c = Number(cost)
  return p > 0 ? ((p - c) / p) * 100 : 0
}

interface Props {
  category: Category
  items: MenuItem[]
  canManage: boolean
  onAddItem: () => void
  onEditCategory: () => void
  onDeleteCategory: () => void
  onEditItem: (item: MenuItem) => void
  onDeleteItem: (item: MenuItem) => void
  onToggleAvailability: (item: MenuItem) => void
}

function IconButton({
  children,
  title,
  onClick,
  danger,
}: {
  children: React.ReactNode
  title: string
  onClick: () => void
  danger?: boolean
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      className={`p-1.5 rounded-[3px] border border-line text-cream-dim transition-colors ${
        danger ? 'hover:text-alert hover:border-alert/50' : 'hover:text-foreground hover:bg-surface-2'
      }`}
    >
      {children}
    </button>
  )
}

export function CategorySection({
  category,
  items,
  canManage,
  onAddItem,
  onEditCategory,
  onDeleteCategory,
  onEditItem,
  onDeleteItem,
  onToggleAvailability,
}: Props) {
  return (
    <div className="ticket-perf relative rounded-[3px] border border-line bg-surface overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-line">
        <div className="flex items-center gap-2.5">
          <span className="w-[3px] h-[18px] bg-accent rounded-[2px]" />
          <div>
            <h2 className="font-display text-lg font-bold tracking-wide text-foreground">
              {category.name}
              {!category.is_active && (
                <span className="ml-2 text-xs text-cream-dim font-normal">(inactive)</span>
              )}
            </h2>
            {category.description && (
              <p className="text-xs text-cream-dim mt-0.5">{category.description}</p>
            )}
          </div>
        </div>
        {canManage && (
          <div className="flex items-center gap-2">
            <IconButton title="Add item" onClick={onAddItem}>
              <Plus size={16} />
            </IconButton>
            <IconButton title="Edit category" onClick={onEditCategory}>
              <Pencil size={16} />
            </IconButton>
            <IconButton title="Delete category" onClick={onDeleteCategory} danger>
              <Trash2 size={16} />
            </IconButton>
          </div>
        )}
      </div>
      {items.length === 0 ? (
        <p className="px-6 py-5 text-sm text-cream-dim">No items in this category yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-cream-dim">
                <th className="text-left py-3 px-6">Item</th>
                <th className="text-right py-3 px-4">Price</th>
                <th className="text-right py-3 px-4">Cost</th>
                <th className="text-right py-3 px-4">Margin</th>
                <th className="text-center py-3 px-4">Status</th>
                {canManage && <th className="text-right py-3 px-6">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-line/50 hover:bg-surface-2/40 transition-colors"
                >
                  <td className="py-3 px-6">
                    <div className="text-foreground font-medium">{item.name}</div>
                    {item.description && (
                      <div className="text-xs text-cream-dim">{item.description}</div>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right text-accent font-semibold">
                    {money(item.price)}
                  </td>
                  <td className="py-3 px-4 text-right text-cream-dim">{money(item.cost_price)}</td>
                  <td className="py-3 px-4 text-right text-electric-300">
                    {marginPct(item.price, item.cost_price).toFixed(1)}%
                  </td>
                  <td className="py-3 px-4 text-center">
                    {item.is_available ? (
                      <span className="text-xs text-success">Available</span>
                    ) : (
                      <span className="text-xs text-cream-dim">Hidden</span>
                    )}
                  </td>
                  {canManage && (
                    <td className="py-3 px-6">
                      <div className="flex items-center justify-end gap-2">
                        <IconButton
                          title={item.is_available ? 'Hide' : 'Show'}
                          onClick={() => onToggleAvailability(item)}
                        >
                          {item.is_available ? <EyeOff size={16} /> : <Eye size={16} />}
                        </IconButton>
                        <IconButton title="Edit" onClick={() => onEditItem(item)}>
                          <Pencil size={16} />
                        </IconButton>
                        <IconButton title="Delete" onClick={() => onDeleteItem(item)} danger>
                          <Trash2 size={16} />
                        </IconButton>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
