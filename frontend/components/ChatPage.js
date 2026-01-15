import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ChatPage({ bookId, onBack }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const history = messages
        .filter((m) => m.role !== 'system')
        .map((m) => ({
          user: m.role === 'user' ? m.content : '',
          assistant: m.role === 'assistant' ? m.content : '',
        }))
        .filter((m) => m.user || m.assistant)

      const response = await axios.post(`${API_URL}/api/v1/query`, {
        book_id: bookId,
        question: userMessage,
        history: history,
      })

      const answer = response.data.answer
      const confidence = response.data.confidence
      const sources = response.data.sources || []

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: answer,
          confidence,
          sources,
          explanation: response.data.explanation,
        },
      ])
    } catch (error) {
      console.error('Query error:', error)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your question.',
          error: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-200px)]">
      <div className="flex items-center mb-4">
        <button
          onClick={onBack}
          className="mr-4 text-blue-600 hover:text-blue-800"
        >
          ← Back
        </button>
        <h2 className="text-2xl font-bold">Chat</h2>
      </div>

      <div className="flex-1 overflow-y-auto bg-white rounded-lg shadow p-6 mb-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 py-12">
            <p>Ask a question about the book to get started.</p>
          </div>
        )}

        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`mb-4 ${
              message.role === 'user' ? 'text-right' : 'text-left'
            }`}
          >
            <div
              className={`inline-block max-w-3xl rounded-lg p-4 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : message.error
                  ? 'bg-red-100 text-red-800'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              {message.confidence !== undefined && (
                <p className="text-xs mt-2 opacity-75">
                  Confidence: {(message.confidence * 100).toFixed(0)}%
                  {message.sources && message.sources.length > 0 && (
                    <span className="ml-2">
                      ({message.sources.length} sources)
                    </span>
                  )}
                </p>
              )}
              {message.explanation && (
                <p className="text-xs mt-1 opacity-75 italic">
                  {message.explanation}
                </p>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="text-left mb-4">
            <div className="inline-block bg-gray-100 rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                <span className="text-gray-600">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex space-x-4">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about the book..."
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </form>
    </div>
  )
}
