'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { UtensilsCrossed, Plus, FolderPlus, Eye, TrendingUp, Lock } from 'lucide-react'
import { StatCard } from '@/components/ui'
import { CategoryFormModal } from '@/components/menu/CategoryFormModal'
import { MenuItemFormModal } from '@/components/menu/MenuItemFormModal'
import { CategorySection } from '@/components/menu/CategorySection'
import { useUserRole } from '@/hooks/useUserRole'
import { showToast } from '@/hooks/useWebSocket'
import {
  fetchCategories,
  fetchMenuItems,
  createCategory,
  updateCategory,
  deleteCategory,
  createMenuItem,
  updateMenuItem,
  deleteMenuItem,
  extractApiError,
} from '@/lib/menu-api'
import type { Category, CategoryInput, MenuItem, MenuItemInput } from '@/types/menu'

const marginPct = (price: number | string, cost: number | string) => {
  const p = Number(price)
  const c = Number(cost)
  return p > 0 ? ((p - c) / p) * 100 : 0
}

export default function MenuPage() {
  const { canManage } = useUserRole()
  const { data, error, isLoading, mutate } = useSWR(
    'menu:all',
    async () => {
      const [categories, items] = await Promise.all([
        fetchCategories(true),
        fetchMenuItems(true),
      ])
      return { categories, items }
    },
    { revalidateOnFocus: false },
  )

  const [itemModalOpen, setItemModalOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null)
  const [presetCategoryId, setPresetCategoryId] = useState<number | null>(null)
  const [categoryModalOpen, setCategoryModalOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)

  const categories = data?.categories ?? []
  const items = data?.items ?? []

  const openAddItem = (categoryId?: number) => {
    setEditingItem(null)
    setPresetCategoryId(categoryId ?? null)
    setItemModalOpen(true)
  }
  const openEditItem = (item: MenuItem) => {
    setEditingItem(item)
    setPresetCategoryId(null)
    setItemModalOpen(true)
  }
  const openAddCategory = () => {
    setEditingCategory(null)
    setCategoryModalOpen(true)
  }
  const openEditCategory = (cat: Category) => {
    setEditingCategory(cat)
    setCategoryModalOpen(true)
  }

  const submitItem = async (input: MenuItemInput) => {
    if (editingItem) {
      await updateMenuItem(editingItem.id, input)
      showToast('Menu item updated', 'success')
    } else {
      await createMenuItem(input)
      showToast('Menu item added', 'success')
    }
    await mutate()
  }

  const submitCategory = async (input: CategoryInput) => {
    if (editingCategory) {
      await updateCategory(editingCategory.id, input)
      showToast('Category updated', 'success')
    } else {
      await createCategory(input)
      showToast('Category added', 'success')
    }
    await mutate()
  }

  const removeItem = async (item: MenuItem) => {
    if (!window.confirm(`Delete "${item.name}"?`)) return
    try {
      await deleteMenuItem(item.id)
      showToast('Item deleted', 'success')
      await mutate()
    } catch (e) {
      showToast(extractApiError(e) || 'Delete failed', 'error')
    }
  }

  const removeCategory = async (cat: Category) => {
    if (!window.confirm(`Delete category "${cat.name}"? Its items will be removed too.`)) return
    try {
      await deleteCategory(cat.id)
      showToast('Category deleted', 'success')
      await mutate()
    } catch (e) {
      showToast(extractApiError(e) || 'Delete failed', 'error')
    }
  }

  const toggleAvailability = async (item: MenuItem) => {
    try {
      await updateMenuItem(item.id, { is_available: !item.is_available })
      await mutate()
    } catch (e) {
      showToast(extractApiError(e) || 'Update failed', 'error')
    }
  }

  const availableCount = items.filter((i) => i.is_available).length
  const avgMargin =
    items.length > 0
      ? items.reduce((sum, i) => sum + marginPct(i.price, i.cost_price), 0) / items.length
      : 0

  return (
    <div className="space-y-8">
      <div className="border-b border-accent/20 pb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold text-foreground mb-1 flex items-center gap-3">
            <UtensilsCrossed size={32} className="text-accent" />
            Menu Management
          </h1>
          <p className="text-cream-dim">
            {canManage
              ? 'Create and manage your own menu items and categories'
              : 'Browse the current menu'}
          </p>
        </div>
        {canManage && (
          <div className="flex gap-3">
            <button
              onClick={openAddCategory}
              className="flex items-center gap-2 px-4 py-2 rounded-[3px] border border-line text-foreground hover:bg-surface-2 transition-colors"
            >
              <FolderPlus size={18} /> Add Category
            </button>
            <button
              onClick={() => openAddItem()}
              disabled={categories.length === 0}
              title={categories.length === 0 ? 'Create a category first' : undefined}
              className="flex items-center gap-2 px-4 py-2 rounded-[3px] bg-accent text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              <Plus size={18} /> Add Item
            </button>
          </div>
        )}
      </div>

      {!canManage && (
        <div className="flex items-center gap-2 text-sm text-cream-dim bg-surface-2 border border-line rounded-[3px] px-4 py-2">
          <Lock size={14} className="text-accent" />
          You have view-only access. Ask an owner or manager to change the menu.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Categories" value={`${categories.length}`} icon={<UtensilsCrossed size={24} />} />
        <StatCard title="Menu Items" value={`${items.length}`} icon={<UtensilsCrossed size={24} />} />
        <StatCard
          title="Available"
          value={`${availableCount}`}
          description={`${items.length - availableCount} hidden`}
          icon={<Eye size={24} />}
        />
        <StatCard title="Avg Margin" value={`${avgMargin.toFixed(1)}%`} icon={<TrendingUp size={24} />} />
      </div>

      {isLoading && <p className="text-cream-dim">Loading menu…</p>}
      {error && (
        <p className="text-alert bg-alert/10 border border-alert/30 rounded-[3px] px-4 py-3">
          Failed to load the menu. Please refresh to retry.
        </p>
      )}

      {!isLoading && !error && categories.length === 0 && (
        <div className="ticket-perf rounded-[3px] border border-line bg-surface px-6 py-12 text-center">
          <UtensilsCrossed size={40} className="text-accent mx-auto mb-3" />
          <h2 className="font-display text-xl font-bold text-foreground mb-1">Your menu is empty</h2>
          <p className="text-cream-dim mb-5">
            {canManage
              ? 'Add your first category, then start adding your real menu items.'
              : 'No menu has been set up yet.'}
          </p>
          {canManage && (
            <button
              onClick={openAddCategory}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-[3px] bg-accent text-white font-medium hover:opacity-90 transition-opacity"
            >
              <FolderPlus size={18} /> Create a category
            </button>
          )}
        </div>
      )}

      <div className="space-y-6">
        {categories.map((cat) => (
          <CategorySection
            key={cat.id}
            category={cat}
            items={items.filter((i) => i.category_id === cat.id)}
            canManage={canManage}
            onAddItem={() => openAddItem(cat.id)}
            onEditCategory={() => openEditCategory(cat)}
            onDeleteCategory={() => removeCategory(cat)}
            onEditItem={openEditItem}
            onDeleteItem={removeItem}
            onToggleAvailability={toggleAvailability}
          />
        ))}
      </div>

      <MenuItemFormModal
        open={itemModalOpen}
        initial={editingItem}
        categories={categories}
        defaultCategoryId={presetCategoryId}
        onClose={() => setItemModalOpen(false)}
        onSubmit={submitItem}
      />
      <CategoryFormModal
        open={categoryModalOpen}
        initial={editingCategory}
        onClose={() => setCategoryModalOpen(false)}
        onSubmit={submitCategory}
      />
    </div>
  )
}
