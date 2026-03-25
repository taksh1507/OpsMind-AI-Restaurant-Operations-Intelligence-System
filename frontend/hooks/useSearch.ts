import { useState } from 'react'

export interface SearchResult {
  id: string
  name: string
  category: 'menu' | 'category' | 'staff'
  description?: string
}

export function useSearch() {
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = async (query: string) => {
    if (!query.trim()) {
      setResults([])
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`)

      if (!response.ok) {
        throw new Error(`Search failed with status ${response.status}`)
      }

      const data = await response.json()
      setResults(data.results || [])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      setError(errorMessage)
      console.error('Search error:', err)
    } finally {
      setLoading(false)
    }
  }

  return { results, loading, error, search }
}
