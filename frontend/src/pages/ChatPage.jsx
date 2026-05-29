import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import api from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import { marked } from 'marked'

export default function ChatPage() {
  const [searchParams] = useSearchParams()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')
  const messagesEndRef = useRef(null)
  const navigate = useNavigate()

  const analysisId = searchParams.get('analysis_id')
  const sessionIdParam = searchParams.get('session_id')

  // ✅ On mode change, fetch sessions for that mode
  useEffect(() => {
    fetchSessions()
  }, [analysisId])

  // ✅ When URL has session_id, load messages for that session
  useEffect(() => {
    if (sessionIdParam) {
      const sid = parseInt(sessionIdParam)
      setSessionId(sid)
      fetchMessages(sid)
    } else {
      setSessionId(null)
      setMessages([])
    }
  }, [sessionIdParam])

  const createNewSession = async () => {
    try {
      setError('')
      const url = analysisId 
        ? `/api/chat/sessions/new?analysis_id=${parseInt(analysisId)}`
        : '/api/chat/sessions/new'

      const response = await api.post(url, {})
      const newSessionId = response.data.id
      
      if (analysisId) {
        navigate(`/chat?session_id=${newSessionId}&analysis_id=${analysisId}`)
      } else {
        navigate(`/chat?session_id=${newSessionId}`)
      }
    } catch (err) {
      console.error('Error creating session:', err)
      setError(err.response?.data?.detail || 'Failed to create chat session')
    }
  }

  const fetchSessions = async () => {
    try {
      let url = '/api/chat/sessions'
      if (analysisId) {
        url += `?analysis_id=${analysisId}`
      }
      // If NO analysisId, backend gets None and filters for analysis_id IS NULL
      
      const response = await api.get(url)
      
      // ✅ FILTER: Only show sessions that have at least 1 message
      const filteredSessions = response.data.filter(s => s.message_count > 0)
      setSessions(filteredSessions)
      setError('')
      
      console.log(`📚 Loaded ${filteredSessions.length} non-empty sessions (analysis_id=${analysisId || 'null'})`)
    } catch (err) {
      console.error('Error fetching sessions:', err)
      if (err.response?.status !== 401) {
        setError('Failed to load chat sessions')
      }
    }
  }

  const fetchMessages = async (sid) => {
    try {
      const response = await api.get(`/api/chat/sessions/${sid}/messages`)
      console.log('Messages fetched:', response.data)
      setMessages(response.data)
      setError('')
    } catch (err) {
      console.error('Error fetching messages:', err)
      setError(err.response?.data?.detail || 'Failed to load messages')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim()) return
    
    // ✅ If no session, create one before sending message
    if (!sessionId) {
      await createNewSession()
      return
    }

    // ✅ REPLACE THIS ENTIRE FUNCTION WITH:

    const userMessage = input
    setInput('')
    setLoading(true)
    setError('')

    try {
      // ✅ ADD USER MESSAGE IMMEDIATELY
      const tempUserMsg = {
        id: Date.now(),
        user_message: userMessage,
        assistant_response: '',
        created_at: new Date().toISOString(),
        sources: [],
        isStreaming: true
      }
      setMessages(prev => [...prev, tempUserMsg])

      // ✅ STREAM THE RESPONSE
      const backendUrl = import.meta.env.VITE_API_URL || 'http://192.168.1.15:8000'
      const response = await fetch(`${backendUrl}/api/chat/message/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          analysis_id: analysisId ? parseInt(analysisId) : null
        })
      })

      if (!response.ok) throw new Error('Stream failed')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let assistantResponse = ''

      // Read stream word by word
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const word = line.slice(6)
            assistantResponse += word

            // ✅ UPDATE MESSAGE WITH STREAMING TEXT
            setMessages(prev => {
              const updated = [...prev]
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                assistant_response: assistantResponse
              }
              return updated
            })
          }
        }
      }

      // Mark as done streaming
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          isStreaming: false
        }
        return updated
      })

      // Refetch sessions/messages
      await fetchSessions()

    } catch (err) {
      console.error('Streaming error:', err)
      setError(err.message || 'Failed to send message')
      // Remove failed message
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-white">
      <div className="w-64 bg-gray-50 border-r border-gray-300 overflow-y-auto">
        <div className="p-4 border-b border-gray-300 space-y-2">
          <button
            onClick={createNewSession}
            className="w-full px-4 py-2 bg-gray-900 text-white rounded-lg font-semibold hover:bg-black transition focus:ring-2 focus:ring-blue-500"
          >
            ➕ New Chat
          </button>
          {analysisId && (
            <button
              onClick={() => navigate('/chat')}
              className="w-full px-4 py-2 bg-gray-500 text-white rounded-lg font-semibold hover:bg-gray-600 transition text-sm"
            >
              🌐 Universal Chat
            </button>
          )}
        </div>

        <div className="p-4 space-y-2">
          <p className="text-xs font-bold text-gray-500 uppercase px-2">Sessions</p>
          {sessions.length === 0 ? (
            <p className="text-xs text-gray-400 px-2">No chats yet</p>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => {
                  if (session.analysis_id) {
                    navigate(`/chat?session_id=${session.id}&analysis_id=${session.analysis_id}`)
                  } else {
                    navigate(`/chat?session_id=${session.id}`)
                  }
                }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                  sessionId === session.id
                    ? 'bg-gray-200 text-gray-900 font-semibold border-l-4 border-blue-600'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
                title={session.title || 'Untitled'}
              >
                <span className="truncate block">{session.title || 'Untitled'}</span>
                <span className="text-xs text-gray-500">{session.message_count} messages</span>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-white">
        {error && (
          <div className="bg-red-50 border-b border-red-300 text-red-700 p-3">
            <p className="text-sm">{error}</p>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {!sessionId ? (
            <div className="text-center text-gray-400 mt-20">
              <p className="text-lg">📝 Click "New Chat" or select a session to start</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center text-gray-400 mt-20">
              <p className="text-lg">💬 Start a conversation!</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-end">
                  <div className="bg-gray-900 text-white px-4 py-2 rounded-lg max-w-xs">
                    {msg.user_message}
                  </div>
                </div>

                <div className="flex justify-start">
                  <div className="bg-white border border-gray-300 px-4 py-2 rounded-lg max-w-2xl prose prose-sm max-w-none">
                    <div
                      dangerouslySetInnerHTML={{
                        __html: marked(msg.assistant_response, {
                          breaks: true,
                          gfm: true,
                        }),
                      }}
                    />
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-gray-200 bg-white p-4">
          {sessionId ? (
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type a message..."
                disabled={loading}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none disabled:opacity-50 transition"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="px-6 py-2 bg-gray-900 text-white font-semibold rounded-lg hover:bg-black disabled:opacity-50 transition flex items-center gap-2 focus:ring-2 focus:ring-blue-500"
              >
                {loading && <LoadingSpinner size="sm" />}
                Send
              </button>
            </form>
          ) : (
            <p className="text-gray-400 text-sm">Create or select a chat to start</p>
          )}
        </div>
      </div>
    </div>
  )
}