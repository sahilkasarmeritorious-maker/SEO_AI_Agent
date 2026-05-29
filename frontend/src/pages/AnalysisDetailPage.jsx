import { useParams, useNavigate } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import LoadingSpinner from '../components/LoadingSpinner'
import ScoreBar from '../components/ScoreBar'

export default function AnalysisDetailPage() {
  const { analysisId } = useParams()
  const navigate = useNavigate()
  const { data: analysis, loading, error } = useFetch(`/api/analysis/results/${analysisId}`)
  
  const parseData = (data) => {
    if (!data) return []
    if (typeof data === 'string') {
      try {
        return JSON.parse(data)
      } catch (e) {
        return [data]
      }
    }
    if (Array.isArray(data)) return data
    return []
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded">
          <h3 className="font-bold mb-2">Error Loading Analysis</h3>
          <p>{error}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="bg-yellow-50 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded">
          <h3 className="font-bold mb-2">Analysis Not Found</h3>
          <p>The analysis you're looking for doesn't exist or has been deleted.</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 transition"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="bg-gradient-to-r from-gray-900 to-black text-white rounded-xl p-8 mb-8">
        <h1 className="text-3xl font-bold mb-2">Analysis Results</h1>
        <p className="text-gray-300">
          Analyzed on {new Date(analysis.created_at).toLocaleDateString()}
        </p>
        <p className="text-sm text-gray-400 mt-2">{analysis.url}</p>
      </div>

      {/* Scores with Animation */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h3 className="text-2xl font-bold text-gray-900 mb-4">SEO Score</h3>
          <ScoreBar label="" score={analysis.seo_overall_score} duration={800} />
          <p className="text-sm text-gray-600 mt-3">Score: {analysis.seo_overall_score}/100</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h3 className="text-2xl font-bold text-gray-900 mb-4">UX Score</h3>
          <ScoreBar label="" score={analysis.ux_overall_score} duration={800} />
          <p className="text-sm text-gray-600 mt-3">Score: {analysis.ux_overall_score}/100</p>
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b-2 border-green-500">
              ✅ SEO Strengths
            </h3>
            <ul className="space-y-2">
              {parseData(analysis.seo_strengths).length > 0 ? (
                parseData(analysis.seo_strengths).map((item, i) => (
                  <li key={i} className="text-gray-600 text-sm">
                    • {typeof item === 'object' ? item.finding || JSON.stringify(item) : item}
                  </li>
                ))
              ) : (
                <li className="text-gray-400 text-sm italic">No strengths found</li>
              )}
            </ul>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b-2 border-yellow-500">
              ⚠️ SEO Weaknesses
            </h3>
            <ul className="space-y-2">
              {parseData(analysis.seo_weaknesses).length > 0 ? (
                parseData(analysis.seo_weaknesses).map((item, i) => (
                  <li key={i} className="text-gray-600 text-sm">
                    • {typeof item === 'object' ? item.finding || JSON.stringify(item) : item}
                  </li>
                ))
              ) : (
                <li className="text-gray-400 text-sm italic">No weaknesses found</li>
              )}
            </ul>
          </div>
        </div>

        <div>
          <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b-2 border-green-500">
              ✅ UX Strengths
            </h3>
            <ul className="space-y-2">
              {parseData(analysis.ux_strengths).length > 0 ? (
                parseData(analysis.ux_strengths).map((item, i) => (
                  <li key={i} className="text-gray-600 text-sm">
                    • {typeof item === 'object' ? item.finding || JSON.stringify(item) : item}
                  </li>
                ))
              ) : (
                <li className="text-gray-400 text-sm italic">No strengths found</li>
              )}
            </ul>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b-2 border-yellow-500">
              ⚠️ UX Weaknesses
            </h3>
            <ul className="space-y-2">
              {parseData(analysis.ux_weaknesses).length > 0 ? (
                parseData(analysis.ux_weaknesses).map((item, i) => (
                  <li key={i} className="text-gray-600 text-sm">
                    • {typeof item === 'object' ? item.finding || JSON.stringify(item) : item}
                  </li>
                ))
              ) : (
                <li className="text-gray-400 text-sm italic">No weaknesses found</li>
              )}
            </ul>
          </div>
        </div>
      </div>

      {/* Back Button */}
      <div className="mt-8">
        <button
          onClick={() => navigate('/dashboard')}
          className="px-6 py-2 bg-gray-900 text-white font-semibold rounded-lg hover:bg-black transition"
        >
          ← Back to Dashboard
        </button>
      </div>
    </div>
  )
}