import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import api from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { login } = useAuthStore()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      // Create form-encoded data (what OAuth2 expects)
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)
    
      const response = await api.post('/api/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      login(response.data.user, response.data.access_token)
      navigate('/dashboard')
    } catch (err) {
      // Handle FastAPI validation errors
      if (err.response?.data?.detail && Array.isArray(err.response.data.detail)) {
        const validationError = err.response.data.detail[0]
        setError(validationError.msg || 'Validation error')
      } 
      // Handle regular error responses
      else if (err.response?.data?.detail) {
        setError(err.response.data.detail)
      } 
      // Handle network errors
      else if (err.message === 'Network Error') {
        setError('Network error - backend not responding')
      }
      // Fallback
      else {
        setError('Login failed')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center px-4">
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Sign In</h1>
        <p className="text-gray-600 mb-6">Welcome back to Website Analyzer</p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
              placeholder="your_username"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-gray-900 text-white font-semibold rounded-lg hover:bg-black disabled:opacity-50 transition flex items-center justify-center gap-2 focus:ring-2 focus:ring-blue-500"
          >
            {loading && <LoadingSpinner size="sm" />}
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="mt-6 text-center text-gray-600">
          Don't have an account?{' '}
          <Link to="/register" className="text-gray-900 font-semibold hover:text-blue-600 transition">
            Register
          </Link>
        </p>
      </div>
    </div>
  )
}