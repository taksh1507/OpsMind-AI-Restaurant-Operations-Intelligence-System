'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import apiClient from '@/lib/api-client'

export interface SearchResult {
  id: string
  name: string
  category: 'menu' | 'category' | 'staff'
  description?: string
}
interface SearchResponse { query: string; count: number; results: SearchResult[] }

export function useSearch() {
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pending = useRef<{ timer?: ReturnType<typeof setTimeout>; controller?: AbortController; generation: number }>({ generation: 0 })

  const cancel = useCallback(() => {
    clearTimeout(pending.current.timer)
    pending.current.controller?.abort()
    pending.current.generation += 1
  }, [])
  const clear = useCallback(() => {
    cancel(); setResults([]); setLoading(false); setError(null)
  }, [cancel])

  const search = useCallback((input: string) => {
    clear()
    const q = input.trim()
    if (!q) return
    const controller = new AbortController()
    const generation = pending.current.generation
    pending.current.controller = controller
    setLoading(true)
    pending.current.timer = setTimeout(async () => {
      try {
        const response = await apiClient.get<SearchResponse>('/search', { params: { q }, signal: controller.signal })
        if (!controller.signal.aborted && generation === pending.current.generation) setResults(response.data.results)
      } catch {
        if (!controller.signal.aborted && generation === pending.current.generation) setError('Search temporarily unavailable. Please try again.')
      } finally {
        if (!controller.signal.aborted && generation === pending.current.generation) setLoading(false)
      }
    }, 250)
  }, [clear])

  useEffect(() => cancel, [cancel])
  return { results, loading, error, search, clear }
}
