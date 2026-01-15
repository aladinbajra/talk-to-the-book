import { useState } from 'react'
import Head from 'next/head'
import BooksList from '../components/BooksList'
import ChatPage from '../components/ChatPage'
import UploadPage from '../components/UploadPage'

export default function Home() {
  const [currentView, setCurrentView] = useState('books') // 'books', 'chat', 'upload'
  const [selectedBookId, setSelectedBookId] = useState(null)

  return (
    <>
      <Head>
        <title>Talk to the Book</title>
        <meta name="description" content="Interactive Q&A for your books" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-2xl font-bold text-gray-900">
                    Talk to the Book
                  </h1>
                </div>
                <div className="ml-10 flex items-center space-x-4">
                  <button
                    onClick={() => setCurrentView('books')}
                    className={`px-3 py-2 rounded-md text-sm font-medium ${
                      currentView === 'books'
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Books
                  </button>
                  <button
                    onClick={() => setCurrentView('upload')}
                    className={`px-3 py-2 rounded-md text-sm font-medium ${
                      currentView === 'upload'
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Upload
                  </button>
                </div>
              </div>
            </div>
          </div>
        </nav>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {currentView === 'books' && (
            <BooksList
              onSelectBook={(bookId) => {
                setSelectedBookId(bookId)
                setCurrentView('chat')
              }}
            />
          )}

          {currentView === 'chat' && selectedBookId && (
            <ChatPage
              bookId={selectedBookId}
              onBack={() => {
                setSelectedBookId(null)
                setCurrentView('books')
              }}
            />
          )}

          {currentView === 'upload' && (
            <UploadPage
              onUploadComplete={(bookId) => {
                setSelectedBookId(bookId)
                setCurrentView('books')
              }}
            />
          )}
        </div>
      </main>
    </>
  )
}
