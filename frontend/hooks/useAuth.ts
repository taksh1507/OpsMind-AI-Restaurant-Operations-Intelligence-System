'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import apiClient from '@/lib/api-client'

/**
 * Hook to protect pages that require authentication
 * Redirects to login if no access token is found
 */
export function useAuth() {
  const router = useRouter()
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    // Check if token exists in localStorage
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token')

      if (!token) {
        // No token, redirect to login
        router.push('/login')
        setIsAuthenticated(false)
      } else {
        setIsAuthenticated(true)
      }
    }
  }, [router])

  return { isAuthenticated }
}

/**
 * Hook to logout user.
 *
 * Revokes the refresh token server-side (the httpOnly cookie is sent
 * automatically and cleared by the server) and clears the client-readable
 * session before redirecting to login.
 */
export function useLogout() {
  const router = useRouter()

  const logout = async () => {
    if (typeof window === 'undefined') return

    // Best-effort server-side revocation. The refresh token rides along as an
    // httpOnly cookie (withCredentials), so no body is needed. Ignore failures —
    // we still clear the local session so the user is logged out regardless.
    try {
      await apiClient.post('/auth/logout', {})
    } catch {
      // Intentionally ignored: logout must always clear the client session.
    }

    localStorage.removeItem('access_token')
    localStorage.removeItem('token_type')
    router.push('/login')
  }

  return { logout }
}
