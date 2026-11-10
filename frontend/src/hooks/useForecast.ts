import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { ForecastResponse } from '../types'

export function useForecast(days: number = 7) {
  const [data, setData] = useState<ForecastResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    api.forecast(days)
      .then((res) => {
        setData(res)
        setError(null)
      })
      .catch((err) => {
        setError(err.message)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [days])

  return { data, loading, error }
}