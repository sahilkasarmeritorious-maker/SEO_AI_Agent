import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import ScoreBar from '../components/ScoreBar'

export default function DashboardPage() {
  const [url, setUrl] = useState('')
  const [analyses, setAnalyses] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    fetchAnalyses()
  }, [])

  const fetchAnalyses = async () => {
    try {
      const response = await api.get('/api/analysis/history?skip=0&limit=10')
      setAnalyses(response.data)
      setError('')
    } catch (err) {
      console.error('Error fetching analyses:', err)
      setError('Failed to load analyses')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
  
    try {
      await api.post('/api/analysis/analyze', { url })
      setUrl('')
      await fetchAnalyses()
    } catch (err) {
      console.error('Analysis error:', err)
      if (err.response?.data?.detail && Array.isArray(err.response.data.detail)) {
        const validationError = err.response.data.detail[0]
        setError(validationError.msg || 'Analysis failed')
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else if (err.message === 'Network Error') {
        setError('Network error - backend not responding')
      } else {
        setError('Analysis failed')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const interval = setInterval(() => {
      analyses.forEach((analysis) => {
        if (analysis.status === 'processing') {
          checkAnalysisStatus(analysis.id)
        }
      })
    }, 8000)

    return () => clearInterval(interval)
  }, [analyses])

  const checkAnalysisStatus = async (analysisId) => {
    try {
      const response = await api.get(`/api/analysis/results/${analysisId}`)
      setAnalyses((prev) =>
        prev.map((a) => (a.id === analysisId ? response.data : a))
      )
    } catch (err) {
      console.error('Error checking status:', err)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="bg-gradient-to-r from-gray-900 to-black text-white rounded-xl p-8 mb-8">
        <h1 className="text-4xl font-bold mb-2">Analyze Your Website</h1>
        <p className="text-gray-300">Get comprehensive SEO and UX insights powered by AI</p>
      </div>

      <div className="bg-white border-2 border-gray-200 rounded-xl p-8 mb-8">
        <form onSubmit={handleSubmit} className="flex gap-3 flex-wrap">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 min-w-64 px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="px-8 py-3 bg-gray-900 text-white font-bold rounded-lg hover:bg-black disabled:opacity-50 transition flex items-center gap-2 focus:ring-2 focus:ring-blue-500"
          >
            {loading && <LoadingSpinner size="sm" />}
            🔍 Analyze
          </button>
        </form>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 rounded">
            {error}
          </div>
        )}
      </div>

      <h2 className="text-2xl font-bold text-gray-900 mb-6">Recent Analyses</h2>

      {analyses.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border-2 border-dashed border-gray-300">
          <p className="text-gray-500 text-lg">🔍 No analyses yet. Submit a URL above to get started!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {analyses.map((analysis) => (
            <AnalysisCard
              key={analysis.id}
              analysis={analysis}
              navigate={navigate}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function AnalysisCard({ analysis, navigate }) {
  const isCompleted = analysis.status === 'completed'
  const isProcessing = analysis.status === 'processing'

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition transform hover:-translate-y-1">
      <div className="bg-gray-50 border-b border-gray-200 p-4 flex justify-between items-start">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 text-sm break-words">{analysis.url}</h3>
        </div>
        <span
          className={`px-3 py-1 rounded-full font-bold text-xs whitespace-nowrap ml-2 ${
            isCompleted
              ? 'bg-green-100 text-green-700'
              : 'bg-yellow-100 text-yellow-700'
          }`}
        >
          {analysis.status.toUpperCase()}
        </span>
      </div>

      {isProcessing ? (
        <div className="p-6 flex items-center gap-3">
          <LoadingSpinner size="md" />
          <p className="text-gray-600 font-medium">Analyzing website...</p>
        </div>
      ) : isCompleted ? (
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <ScoreBar label="SEO Score" score={analysis.seo_overall_score} duration={800} />
            <ScoreBar label="UX Score" score={analysis.ux_overall_score} duration={800} />
          </div>
        </div>
      ) : null}

      <div className="border-t border-gray-200 p-4 flex gap-2 flex-wrap">
        {isCompleted && (
          <button
            onClick={() => navigate(`/analysis/${analysis.id}`)}
            className="flex-1 px-3 py-2 bg-gray-100 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-200 transition"
          >
            📊 View Details
          </button>
        )}
        <button
          onClick={() => navigate(`/chat?analysis_id=${analysis.id}`)}
          className="flex-1 px-3 py-2 bg-gray-900 text-white text-sm font-semibold rounded-lg hover:bg-black transition focus:ring-2 focus:ring-blue-500"
        >
          💬 Ask Questions
        </button>
      </div>
    </div>
  )
}