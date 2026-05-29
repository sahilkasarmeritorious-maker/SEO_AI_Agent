import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function LandingPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [displayedText, setDisplayedText] = useState('')
  const [lineNumber, setLineNumber] = useState(1)

  const line1 = "Get your Webpage's SEO and UX report's as well as Analysis"
  const line2 = "AI Chat Available Now"

  // ✅ If user is logged in, redirect to dashboard
  useEffect(() => {
    if (isAuthenticated || localStorage.getItem('access_token')) {
      navigate('/dashboard', { replace: true })
    }
  }, [navigate, isAuthenticated])

  // ✅ Typing animation effect with loop
  useEffect(() => {
    const currentText = lineNumber === 1 ? line1 : line2
    
    if (displayedText.length < currentText.length) {
      // Still typing current line
      const timer = setTimeout(() => {
        setDisplayedText(currentText.slice(0, displayedText.length + 1))
      }, 100)
      return () => clearTimeout(timer)
    } else if (displayedText.length === currentText.length) {
      // Finished typing current line
      if (lineNumber === 1) {
        // Move to line 2 after pause
        const timer = setTimeout(() => {
          setLineNumber(2)
          setDisplayedText('')
        }, 1500)
        return () => clearTimeout(timer)
      } else if (lineNumber === 2) {
        // Loop back to line 1 after pause
        const timer = setTimeout(() => {
          setLineNumber(1)
          setDisplayedText('')
        }, 2000)
        return () => clearTimeout(timer)
      }
    }
  }, [displayedText, lineNumber, line1, line2])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center px-4">
      <div className="text-center max-w-2xl">
        {/* Animated Text */}
        <div className="mb-12">
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-8">
            Website Analyzer
          </h1>
          
          {/* Typing Animation (Single Line) */}
          <div className="h-32 flex items-center justify-center">
            <p className="text-2xl md:text-3xl text-blue-400 font-semibold min-h-12">
              {displayedText}
              <span className={`inline-block w-1 h-8 ml-1 bg-blue-400 ${displayedText.length > 0 ? 'animate-pulse' : ''}`}></span>
            </p>
          </div>
        </div>

        {/* Features */}
        <div className="flex gap-4 justify-center mb-8 flex-wrap">
          <button className="px-6 py-2 bg-gray-700 text-white rounded-lg font-semibold hover:bg-gray-600 transition">
            📊 SEO Analysis
          </button>
          <button className="px-6 py-2 bg-gray-700 text-white rounded-lg font-semibold hover:bg-gray-600 transition">
            ⭐ UX Scoring
          </button>
          <button className="px-6 py-2 bg-gray-700 text-white rounded-lg font-semibold hover:bg-gray-600 transition">
            💬 AI Chat
          </button>
        </div>

        {/* CTA Buttons */}
        <div className="flex gap-4 justify-center flex-wrap">
          <a href="/login" className="px-8 py-3 bg-white text-gray-900 rounded-lg font-semibold hover:bg-gray-100 transition">
            Sign In
          </a>
          <a href="/register" className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition">
            Get Started
          </a>
        </div>

        {/* Footer */}
        <p className="text-gray-400 text-sm mt-12">🔐 Secure • ⚡ Fast • 🧠 Intelligent</p>
      </div>
    </div>
  )
}