'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

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
 * Hook to logout user
 */
export function useLogout() {
  const router = useRouter()

  const logout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token')
      localStorage.removeItem('token_type')
      router.push('/login')
    }
  }

  return { logout }
}
