import { useEffect, useRef, useState } from 'react'
import { api, statusLabels, processing } from '../services/api'

const tones = ['clay', 'forest', 'sand', 'blue', 'plum', 'olive']

export default function BooksList({ onSelectBook, onUpload }) {
  const [books, setBooks] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [retry, setRetry] = useState(0)
  const [busy, setBusy] = useState('')
  const [confirm, setConfirm] = useState('')
  const action = useRef(null)
  useEffect(() => {
    const controller = new AbortController()
    let timer
    const load = async () => {
      try {
        const data = await api('/books', { signal: controller.signal })
        if (!controller.signal.aborted) {
          setBooks(data.books || [])
          setError('')
          if ((data.books || []).some(book => processing(book.ingest_status))) timer = setTimeout(load, 2500)
        }
      } catch (failure) { if (!controller.signal.aborted) setError(failure.message) }
    }
    void load()
    return () => { controller.abort(); clearTimeout(timer); action.current?.abort() }
  }, [retry])
  const start = async book => {
    setBusy(book.book_id)
    action.current = new AbortController()
    try {
      await api('/ingest/start', { method: 'POST', body: JSON.stringify({ book_id: book.book_id }), signal: action.current.signal })
      setRetry(value => value + 1)
    } catch (failure) { if (!action.current.signal.aborted) setError(failure.message) }
    finally { setBusy('') }
  }
  const remove = async book => {
    setBusy(book.book_id)
    try {
      await api('/delete_book', { method: 'POST', body: JSON.stringify({ book_id: book.book_id }) })
      setBooks(previous => previous.filter(item => item.book_id !== book.book_id))
      setConfirm('')
    } catch (failure) { setError(failure.message) }
    finally { setBusy('') }
  }
  const ready = (books || []).filter(book => book.ingest_status === 'ready').length
  const visible = (books || []).filter(book => (filter === 'all' || (filter === 'ready' ? book.ingest_status === 'ready' : book.ingest_status !== 'ready')) && `${book.title} ${book.author || ''}`.toLowerCase().includes(query.trim().toLowerCase()))
  return <>
    <div className="eyebrow">A SHELF FULL OF POSSIBILITIES</div>
    <div className="page-heading"><div><h1>Your books.<br /><em>New perspectives.</em></h1><p>Pick up where you left off, or start a new conversation.</p></div><button className="button primary" onClick={onUpload}><span aria-hidden="true">＋</span> Add a book</button></div>
    <div className="library-stats"><div><span className="stat-number">{books ? books.length.toString().padStart(2, '0') : '—'}</span><span>Books in your library</span></div><div><span className="stat-number">{books ? ready.toString().padStart(2, '0') : '—'}</span><span>Ready to explore</span></div><div><span className="stat-number">{books ? books.reduce((sum, book) => sum + (book.question_count || 0), 0).toString().padStart(2, '0') : '—'}</span><span>Questions asked</span></div></div>
    <div className="library-toolbar"><div className="filter-tabs" role="group" aria-label="Filter library">{[['all', 'All books'], ['ready', 'Ready to read'], ['pending', 'Processing & other']].map(([value, label]) => <button key={value} aria-pressed={filter === value} className={filter === value ? 'selected' : ''} onClick={() => setFilter(value)}>{label}</button>)}</div><label className="search-field"><span aria-hidden="true">⌕</span><input type="search" aria-label="Search your books" placeholder="Find a book or author" value={query} onChange={event => setQuery(event.target.value)} /></label></div>
    {error && <div className="notice error" role="alert"><div><strong>We couldn’t complete that request.</strong><p>{error}</p></div><button className="text-button" onClick={() => setRetry(value => value + 1)}>Try again ↗</button></div>}
    {!books && !error && <div className="book-grid" aria-label="Loading books" role="status">{[0, 1, 2].map(number => <div key={number} className="book-skeleton" />)}<span className="sr-only">Loading your library…</span></div>}
    {books && visible.length === 0 && <div className="empty-state"><span className="empty-symbol" aria-hidden="true">▤</span><h2>{books.length ? 'A little more room to look.' : 'Your next chapter starts here.'}</h2><p>{books.length ? 'Try another search or choose All books.' : 'Add a book, ask a question, and follow the ideas that stay with you.'}</p>{books.length ? <button className="button secondary" onClick={() => { setQuery(''); setFilter('all') }}>Clear search & filters</button> : <button className="button primary" onClick={onUpload}>Add your first book ↗</button>}</div>}
    <div className="book-grid">{visible.map((book, index) => <article className="book-card" key={book.book_id}>
      <div className={`book-cover ${tones[index % tones.length]}`}><span className="cover-format">{book.file_format || 'BOOK'} / YOUR LIBRARY</span><span className="cover-ornament" aria-hidden="true">✳</span><h2>{book.title || 'Untitled book'}</h2><span className="cover-author">{book.author || 'A book worth exploring'}</span><span className="cover-line" /></div>
      <div className="book-details"><div className="book-status-row"><span className={`book-status ${book.ingest_status}`}><span className="status-dot" /> {statusLabels[book.ingest_status] || book.ingest_status}</span><span className="book-word-count">{book.total_words ? `${Math.round(book.total_words / 1000)}k words` : book.file_format?.toUpperCase()}</span></div>
        <h3>{book.title || 'Untitled book'}</h3><p>{book.author || 'Your personal copy'}</p>
        {processing(book.ingest_status) && <div className="processing-line" role="status"><span />{statusLabels[book.ingest_status]}…</div>}
        <div className="book-actions">{book.ingest_status === 'ready' ? <button className="text-button" onClick={() => onSelectBook(book)}>Open conversation <span aria-hidden="true">↗</span></button> : !processing(book.ingest_status) ? <button className="text-button" disabled={busy === book.book_id} onClick={() => void start(book)}>{busy === book.book_id ? 'Starting…' : book.ingest_status === 'error' ? 'Retry processing ↗' : 'Start processing ↗'}</button> : <span className="muted">You can leave this page open.</span>}
        <button className="delete-button" disabled={processing(book.ingest_status) || busy === book.book_id} onClick={() => setConfirm(book.book_id)} aria-label={`Delete ${book.title}`}>×</button></div>
        {confirm === book.book_id && <div className="delete-confirm" role="alert"><p>Delete this book and its conversations permanently?</p><button className="text-button danger" disabled={busy === book.book_id} onClick={() => void remove(book)}>Delete book</button><button className="text-button" onClick={() => setConfirm('')}>Keep book</button></div>}
      </div>
    </article>)}</div>
    {books?.length > 0 && <p className="library-footnote">Every answer is connected to the passages behind it. Stay curious.</p>}
  </>
}
