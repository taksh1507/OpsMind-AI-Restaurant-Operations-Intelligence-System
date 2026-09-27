// Thin API layer for menu management (categories + items). Wraps the tenant-
// scoped CRUD endpoints in app/api/categories.py and app/api/menu_items.py.
// Write operations (create/update/delete) require OWNER or MANAGER server-side.

import apiClient from './api-client'
import type {
  Category,
  CategoryInput,
  MenuItem,
  MenuItemInput,
} from '@/types/menu'

// --- Categories ---

export async function fetchCategories(includeInactive = true): Promise<Category[]> {
  const { data } = await apiClient.get<Category[]>('/categories', {
    params: { include_inactive: includeInactive },
  })
  return data
}

export async function createCategory(input: CategoryInput): Promise<Category> {
  const { data } = await apiClient.post<Category>('/categories', input)
  return data
}

export async function updateCategory(
  id: number,
  input: Partial<CategoryInput>,
): Promise<Category> {
  const { data } = await apiClient.put<Category>(`/categories/${id}`, input)
  return data
}

export async function deleteCategory(id: number): Promise<void> {
  await apiClient.delete(`/categories/${id}`)
}

// --- Menu items ---

export async function fetchMenuItems(includeUnavailable = true): Promise<MenuItem[]> {
  const { data } = await apiClient.get<MenuItem[]>('/menu-items', {
    params: { include_unavailable: includeUnavailable },
  })
  return data
}

export async function createMenuItem(input: MenuItemInput): Promise<MenuItem> {
  const { data } = await apiClient.post<MenuItem>('/menu-items', input)
  return data
}

export async function updateMenuItem(
  id: number,
  input: Partial<MenuItemInput>,
): Promise<MenuItem> {
  const { data } = await apiClient.put<MenuItem>(`/menu-items/${id}`, input)
  return data
}

export async function deleteMenuItem(id: number): Promise<void> {
  await apiClient.delete(`/menu-items/${id}`)
}

/** Pull a human-readable message out of a FastAPI/Axios error, if any. */
export function extractApiError(err: unknown): string | null {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
    ?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && (detail[0] as { msg?: string })?.msg) {
    return (detail[0] as { msg: string }).msg
  }
  return null
}
