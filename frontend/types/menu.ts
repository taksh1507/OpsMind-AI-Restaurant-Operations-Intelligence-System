// Menu domain types. Mirrors the backend Category / MenuItem response schemas
// (app/models/schemas.py). Prices arrive as strings when the API serialises
// Decimal, so treat them as `number | string` and coerce with Number() at use.

export interface Category {
  id: number
  tenant_id: number
  name: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface MenuItem {
  id: number
  tenant_id: number
  category_id: number
  name: string
  description: string | null
  price: number | string
  cost_price: number | string
  is_available: boolean
  created_at: string
  updated_at: string
}

export interface CategoryInput {
  name: string
  description?: string | null
  is_active?: boolean
}

export interface MenuItemInput {
  category_id: number
  name: string
  description?: string | null
  price: number
  cost_price: number
  is_available?: boolean
}
