import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'

function conversationTurns(messages) {
  const turns = []
  for (const message of messages) {
    if (message.role === 'user') turns.push({ user: message.content, assistant: '' })
    else if (turns.length) turns[turns.length - 1].assistant = message.content
  }
  return turns.filter(turn => turn.assistant).slice(-5)
}

export default function ChatPage({ bookId, title, onBack }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastQuestion, setLastQuestion] = useState('')
  const end = useRef(null)
  const request = useRef(null)
  const composer = useRef(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, loading])
  useEffect(() => () => request.current?.abort(), [])
  const send = async (question, retry = false) => {
    question = question.trim()
    if (!question || question.length > 4000 || loading) return
    if (!retry) setMessages(previous => [...previous, { role: 'user', content: question }])
    setLastQuestion(question)
    setInput('')
    setLoading(true)
    setError('')
    const controller = new AbortController()
    request.current = controller
    try {
      const answer = await api('/query', { method: 'POST', body: JSON.stringify({ book_id: bookId, question, history: conversationTurns(messages) }), signal: controller.signal })
      if (!controller.signal.aborted) setMessages(previous => [...previous, { role: 'assistant', content: answer.answer, ...answer }])
    } catch (failure) { if (!controller.signal.aborted) setError(failure.message) }
    finally { if (!controller.signal.aborted) { setLoading(false); composer.current?.focus() } }
  }
  const starters = ['What are the main ideas in this book?', 'Summarize the opening chapter.', 'Which passages explain the central theme?']
  return <div className="chat-layout">
    <div className="chat-header"><button className="text-button" onClick={onBack}>← Library</button><div><span className="eyebrow">IN CONVERSATION WITH</span><h1>{title || 'Your book'}</h1></div><span className="source-badge"><span className="status-dot" /> Answers with sources</span></div>
    <div className="chat-messages" role="log" aria-label="Conversation" aria-live="polite">
      {messages.length === 0 && <div className="chat-welcome"><div className="chat-flower" aria-hidden="true">✳</div><h2>There’s more<br /><em>between the lines.</em></h2><p>Ask a question. Follow an idea. Find the passage that makes it click.</p><div className="starter-questions">{starters.map(question => <button key={question} disabled={loading} onClick={() => void send(question)}>{question}<span aria-hidden="true">↗</span></button>)}</div></div>}
      {messages.map((message, index) => <article className={`message ${message.role}`} key={index}><div className="message-label">{message.role === 'user' ? 'YOU' : 'YOUR READING COMPANION'}</div><p className="message-body">{message.content === 'UNKNOWN IN BOOK' ? 'I couldn’t find support for an answer in this book. Try asking about a specific chapter or idea.' : message.content}</p>
        {message.role === 'assistant' && message.source_details?.length > 0 && <div className="source-passages"><div className="source-heading">READ THE PASSAGES BEHIND THIS ANSWER <span>{message.source_details.length}</span></div>{message.source_details.map((source, position) => <details key={source.chunk_id}><summary><span className="citation-number">{position + 1}</span>{source.chapter ? `Chapter ${source.chapter}` : 'Book passage'} <span className="source-location">{source.start_loc?.replace('word_', 'Word ')}</span><span aria-hidden="true">＋</span></summary><blockquote>{source.excerpt}</blockquote></details>)}</div>}
        {message.role === 'assistant' && message.sources?.length > 0 && !message.source_details?.length && <p className="citation-fallback">Sources: {message.sources.join(', ')}</p>}
      </article>)}
      {loading && <div className="thinking" role="status"><span className="spinner" />Looking through the book…</div>}
      {error && <div className="notice error" role="alert" aria-label="Question failed"><p>{error}</p><button className="text-button" onClick={() => void send(lastQuestion, true)}>Retry this question ↗</button></div>}
      <div ref={end} />
    </div>
    <form className="chat-composer" onSubmit={event => { event.preventDefault(); void send(input) }}><label className="sr-only" htmlFor="question">Ask a question about this book</label><textarea id="question" ref={composer} value={input} maxLength={4000} rows={2} onChange={event => setInput(event.target.value)} placeholder="What would you like to discover?" disabled={loading} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send(input) } }} /><button type="submit" className="send-button" aria-label="Send question" disabled={loading || !input.trim()}>↑</button><div className="composer-footer"><span>Answers draw from your book. Open a source passage to explore further.</span><span>{input.length}/4000</span></div></form>
  </div>
}
