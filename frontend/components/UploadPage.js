import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'

export default function UploadPage({ onUploadComplete, onBack }) {
  const [file, setFile] = useState(null)
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [bookId, setBookId] = useState(null)
  const [stage, setStage] = useState('')
  const [dragging, setDragging] = useState(false)
  const input = useRef(null)
  const request = useRef(null)
  useEffect(() => () => request.current?.abort(), [])
  const choose = selected => {
    setError('')
    if (!selected) return
    if (!/\.(pdf|txt|epub)$/i.test(selected.name)) return setError('Please choose a PDF, TXT, or ePub file.')
    if (!selected.size || selected.size > 100 * 1024 * 1024) return setError('Choose a non-empty file smaller than 100 MB.')
    setFile(selected)
    setBookId(null)
  }
  const submit = async event => {
    event.preventDefault()
    if ((!file && !bookId) || !consent || busy) return
    const controller = new AbortController()
    request.current = controller
    setBusy(true)
    setError('')
    try {
      let id = bookId
      if (!id) {
        setStage('Uploading your book…')
        const form = new FormData()
        form.append('file', file)
        form.append('user_consent', String(consent))
        id = (await api('/upload', { method: 'POST', body: form, signal: controller.signal })).book_id
        setBookId(id)
      }
      setStage('Starting book processing…')
      await api('/ingest/start', { method: 'POST', body: JSON.stringify({ book_id: id }), signal: controller.signal })
      onUploadComplete(id)
    } catch (failure) { if (!controller.signal.aborted) setError(failure.message || 'Please try again.') }
    finally { if (!controller.signal.aborted) setBusy(false) }
  }
  return <div className="upload-page"><button className="text-button back-button" onClick={onBack}>← Back to your library</button><div className="eyebrow">MAKE ROOM FOR SOMETHING GOOD</div><h1>A new book.<br /><em>A new conversation.</em></h1><p className="page-description">Bring a book you love. We’ll help you explore it, one question at a time.</p>
    <form onSubmit={submit} className="upload-panel">
      <div className={`drop-zone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); if (!busy) setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); if (!busy) choose(event.dataTransfer.files[0]) }}>
        <span className="upload-symbol" aria-hidden="true">↑</span><h2>{file ? file.name : 'Drop your book right here'}</h2><p>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · Ready to upload` : 'or choose a file from your computer'}</p><button type="button" className="button secondary" disabled={busy} onClick={() => input.current?.click()}>{file ? 'Choose another file' : 'Browse files'}</button><input ref={input} className="sr-only" type="file" aria-label="Choose a book file" accept=".pdf,.txt,.epub" disabled={busy} onChange={event => choose(event.target.files[0])} /><small>PDF, TXT or ePub · Up to 100 MB</small>
      </div>
      <label className="consent-check"><input type="checkbox" checked={consent} disabled={busy} onChange={event => setConsent(event.target.checked)} /><span>I have the right to upload this book and agree to have it processed for personal questions and answers.</span></label>
      {error && <div className="notice error" role="alert"><p>{error}</p>{bookId && <small>Your book is saved. Retry processing without uploading it again.</small>}</div>}
      {busy && <p className="upload-progress" role="status"><span className="spinner" />{stage}</p>}
      <button className="button primary full-width" type="submit" disabled={busy || !file || !consent}>{busy ? 'Please wait…' : bookId ? 'Retry processing ↗' : 'Add to my library ↗'}</button>
      <p className="upload-privacy">Processing may take a few minutes. Follow the progress in your library.</p>
    </form>
    <div className="upload-steps"><div><b>01</b><span>Add your book</span></div><div><b>02</b><span>We organize its passages</span></div><div><b>03</b><span>Follow your curiosity</span></div></div>
  </div>
}
