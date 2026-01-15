import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function BooksList({ onSelectBook }) {
  const [books, setBooks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchBooks()
  }, [])

  const fetchBooks = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/api/v1/books`)
      setBooks(response.data.books || [])
      setError(null)
    } catch (err) {
      setError('Failed to load books')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-4 text-gray-600">Loading books...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <p className="text-red-800">{error}</p>
        <button
          onClick={fetchBooks}
          className="mt-2 text-red-600 hover:text-red-800 underline"
        >
          Retry
        </button>
      </div>
    )
  }

  if (books.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 mb-4">No books uploaded yet.</p>
        <p className="text-sm text-gray-500">
          Upload a book to get started.
        </p>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Your Books</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {books.map((book) => (
          <div
            key={book.book_id}
            className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => book.ingest_status === 'ready' && onSelectBook(book.book_id)}
          >
            <h3 className="text-xl font-semibold mb-2">{book.title || 'Untitled'}</h3>
            {book.author && (
              <p className="text-gray-600 text-sm mb-2">by {book.author}</p>
            )}
            <div className="flex items-center justify-between mt-4">
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${
                  book.ingest_status === 'ready'
                    ? 'bg-green-100 text-green-800'
                    : book.ingest_status === 'error'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}
              >
                {book.ingest_status}
              </span>
              {book.question_count > 0 && (
                <span className="text-sm text-gray-500">
                  {book.question_count} questions
                </span>
              )}
            </div>
            {book.ingest_status !== 'ready' && (
              <p className="text-xs text-gray-500 mt-2">
                {book.ingest_status === 'uploaded' && 'Click to start ingest'}
                {book.ingest_status === 'parsing' && 'Parsing...'}
                {book.ingest_status === 'chunking' && 'Chunking...'}
                {book.ingest_status === 'embedding' && 'Generating embeddings...'}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
