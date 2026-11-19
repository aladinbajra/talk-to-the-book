import { useState } from 'react'
import Head from 'next/head'
import BooksList from '../components/BooksList'
import ChatPage from '../components/ChatPage'
import UploadPage from '../components/UploadPage'

export default function Home() {
  const [view, setView] = useState('books')
  const [book, setBook] = useState(null)
  return <>
    <Head><title>Talk to the Book — Your reading companion</title><meta name="description" content="A quiet place to read between the lines. Ask your books questions and explore the passages behind every answer." /><meta name="viewport" content="width=device-width, initial-scale=1" /></Head>
    <a className="skip-link" href="#workspace">Skip to content</a>
    <div className="app-shell">
      <aside className="sidebar">
        <a href="#" onClick={event => { event.preventDefault(); setView('books') }} className="brand"><span className="brand-mark" aria-hidden="true">b.</span><span>Talk to<br /><strong>the Book</strong></span></a>
        <div className="sidebar-label">YOUR SPACE</div>
        <nav aria-label="Main navigation">
          <button className={`nav-item ${view === 'books' ? 'active' : ''}`} aria-current={view === 'books' ? 'page' : undefined} onClick={() => setView('books')}><span aria-hidden="true">▤</span> My library <span className="nav-arrow">↗</span></button>
          <button className={`nav-item ${view === 'upload' ? 'active' : ''}`} aria-current={view === 'upload' ? 'page' : undefined} onClick={() => setView('upload')}><span aria-hidden="true">＋</span> Add a book</button>
        </nav>
        <div className="sidebar-note"><span className="tiny-book" aria-hidden="true">❧</span><p>Good books have<br /><em>more to say.</em></p><small>Keep the conversation going.</small></div>
        <div className="sidebar-bottom"><span className="status-dot" /> Your personal reading space</div>
      </aside>
      <div className="main-column">
        <header className="topbar"><span>YOUR READING COMPANION</span><span className="topbar-note">Read. Question. Discover.</span></header>
        <main id="workspace" className={`workspace ${view === 'chat' ? 'chat-workspace' : ''}`}>
          {view === 'books' && <BooksList onSelectBook={selected => { setBook(selected); setView('chat') }} onUpload={() => setView('upload')} />}
          {view === 'upload' && <UploadPage onUploadComplete={() => setView('books')} onBack={() => setView('books')} />}
          {view === 'chat' && book && <ChatPage key={book.book_id} bookId={book.book_id} title={book.title} onBack={() => setView('books')} />}
        </main>
        <footer className="page-footer"><span>A little curiosity goes a long way.</span><span>Talk to the Book <span aria-hidden="true">↗</span></span></footer>
      </div>
    </div>
  </>
}
