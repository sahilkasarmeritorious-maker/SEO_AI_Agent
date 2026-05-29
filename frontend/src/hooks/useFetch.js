import { useState, useEffect } from 'react'
import api from '../services/api'

export const useFetch = (url, options = {}) => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!url) {
      setLoading(false)
      return
    }

    const fetchData = async () => {
      try {
        setLoading(true)
        const response = await api.get(url)
        setData(response.data)
        setError(null)
      } catch (err) {
        setError(err.response?.data?.detail || 'Error fetching data')
        setData(null)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [url])

  const refetch = async () => {
    if (!url) return
    try {
      setLoading(true)
      const response = await api.get(url)
      setData(response.data)
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error fetching data')
    } finally {
      setLoading(false)
    }
  }

  return { data, loading, error, refetch }
}