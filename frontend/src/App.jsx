import { useEffect, useRef, useState } from 'react'

const SUGGESTIONS = [
  'Where is order 100004?',
  'Show me the items in order 100001',
  'What orders does customer 50001 have?',
  'What is the refund status of order 100002?',
]

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [health, setHealth] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    fetch('/api/health')
      .then((res) => (res.ok ? res.json() : res.json().then((d) => Promise.reject(new Error(d.detail || res.statusText)))))
      .then(setHealth)
      .catch((err) => setHealth({ status: 'down', error: String(err.message || err) }))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send(text) {
    const content = (text ?? input).trim()
    if (!content || loading) return

    const history = messages
    setInput('')
    setError('')
    setMessages((prev) => [...prev, { role: 'user', content }])
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, history }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || res.statusText)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
    } catch (err) {
      setError(err.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  const statusOk = health?.status === 'ok'

  return (
    <div className="app">
      <header className="header">
        <h1>Retail Support Assistant</h1>
        <div className={`status ${statusOk ? 'ok' : 'bad'}`}>
          <span className="dot" />
          {health === null
            ? 'checking…'
            : statusOk
              ? `MCP connected · ${health.tools.length} tools · ${health.provider}: ${health.model}`
              : 'MCP unavailable'}
        </div>
      </header>

      <main className="messages">
        {messages.length === 0 && (
          <div className="empty">
            <p>Ask about an order — status, shipping, history, refunds.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} disabled={loading}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <span className="who">{m.role === 'user' ? 'You' : 'Assistant'}</span>
            <p>{m.content}</p>
          </div>
        ))}

        {loading && <div className="bubble assistant typing">Thinking…</div>}
        {error && <div className="error">{error}</div>}
        <div ref={bottomRef} />
      </main>

      <footer className="composer">
        <input
          value={input}
          placeholder="Ask your question…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          disabled={loading}
        />
        <button onClick={() => send()} disabled={loading || !input.trim()}>
          {loading ? '…' : 'Send'}
        </button>
      </footer>
    </div>
  )
}
