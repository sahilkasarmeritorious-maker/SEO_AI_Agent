import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link 
          to={isAuthenticated ? "/dashboard" : "/"} 
          className="flex items-center gap-2 text-xl font-bold text-gray-900 hover:text-blue-600 transition"
        >
          🔍 Website Analyzer
        </Link>

        <div className="flex items-center gap-4">
          {isAuthenticated && user ? (
            <>
              <span className="text-sm text-gray-600">{user.email}</span>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition focus:ring-2 focus:ring-blue-500"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="px-4 py-2 text-gray-600 hover:text-gray-900 font-semibold transition"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="px-4 py-2 bg-gray-900 text-white rounded-lg font-semibold hover:bg-black transition focus:ring-2 focus:ring-blue-500"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}