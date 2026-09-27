'use client'

import { useEffect, useState } from 'react'

export type UserRole = 'owner' | 'manager' | 'staff'

/**
 * Reads the current user's role from the JWT access token (`role` claim),
 * mirroring the decode used in the Sidebar. `canManage` is owner|manager — the
 * roles the backend allows to create/edit/delete menu data (get_current_manager).
 */
export function useUserRole() {
  const [role, setRole] = useState<UserRole | null>(null)
  const [userId, setUserId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    try {
      const token =
        typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
      if (!token) {
        setRole(null)
        return
      }
      const parts = token.split('.')
      if (parts.length !== 3) {
        setRole(null)
        return
      }
      // JWT payloads are base64url; normalise before decoding.
      const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(atob(b64))
      setRole((payload.role as UserRole) || 'staff')
      setUserId(typeof payload.user_id === 'number' ? payload.user_id : null)
    } catch {
      setRole(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const canManage = role === 'owner' || role === 'manager'
  const isOwner = role === 'owner'
  return { role, userId, canManage, isOwner, loading }
}
