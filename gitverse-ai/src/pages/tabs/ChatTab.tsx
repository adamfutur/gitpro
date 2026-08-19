import { useEffect, useRef, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { createChatSession, sendChatMessage } from '../../api'
import Spinner from '../../components/Spinner'
import type { RepoOutletContext } from '../RepoDetail'
import './ChatTab.css'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatTab() {
  const { repo } = useOutletContext<RepoOutletContext>()
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setSessionId(null)
    setMessages([])
    createChatSession(repo.id, `Chat about ${repo.name}`)
      .then((res) => setSessionId(res.session_id))
      .catch((err) => setError(err.message ?? 'Failed to start chat session'))
  }, [repo.id, repo.name])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

  async function handleSend() {
    const text = input.trim()
    if (!text || !sessionId || sending) return

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    setError(null)

    try {
      const res = await sendChatMessage(sessionId, text)
      setMessages((prev) => [...prev, { role: 'assistant', content: res.response }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="card gc-chat">
      <div className="gc-chat-messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="gc-chat-empty">
            Ask anything about <strong>{repo.full_name}</strong> — its README, files, recent
            commits, or pull requests.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`gc-chat-bubble gc-chat-bubble-${m.role}`}>
            {m.content}
          </div>
        ))}
        {sending && (
          <div className="gc-chat-bubble gc-chat-bubble-assistant gc-chat-typing">
            <Spinner />
          </div>
        )}
      </div>

      {error && <p className="gc-chat-error">{error}</p>}

      <div className="gc-chat-input-row">
        <textarea
          className="gc-chat-input"
          placeholder={sessionId ? 'Message gitcat...' : 'Starting chat session...'}
          value={input}
          disabled={!sessionId}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
        />
        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={!sessionId || !input.trim() || sending}
        >
          Send
        </button>
      </div>
    </div>
  )
}
