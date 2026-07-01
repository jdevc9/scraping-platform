import { useState, useEffect, useCallback, useRef } from 'react'

interface UseApiOptions {
  /** Auto-refresh interval in ms. 0 = no polling. */
  pollInterval?: number
  /** Don't fetch on mount */
  lazy?: boolean
}

interface UseApiResult<T> {
  data: T | null
  error: string | null
  isLoading: boolean
  refetch: () => void
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options: UseApiOptions = {},
): UseApiResult<T> {
  const { pollInterval = 0, lazy = false } = options
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(!lazy)
  const intervalRef = useRef<ReturnType<typeof setInterval>>()

  const fetch = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await fetcher()
      setData(result)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } }; message?: string })
        ?.response?.data?.detail ?? (err as { message?: string })?.message ?? 'Unknown error'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!lazy) fetch()
  }, [fetch, lazy])

  useEffect(() => {
    if (pollInterval > 0) {
      intervalRef.current = setInterval(fetch, pollInterval)
      return () => clearInterval(intervalRef.current)
    }
  }, [fetch, pollInterval])

  return { data, error, isLoading, refetch: fetch }
}
