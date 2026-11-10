import { useState } from 'react'
import { Send, Bot, User } from 'lucide-react'
import { api } from '../services/api'

interface Msg {
  role: 'user' | 'assistant'
  content: string
  tools?: string[]
}

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function send() {
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setBusy(true)
    setError(null)
    setMessages((m) => [...m, { role: 'user', content: text }])

    try {
      const res = await api.chat(text, sessionId)
      setSessionId(res.session_id)
      setMessages((m) => [...m, { role: 'assistant', content: res.answer, tools: res.tools_used }])
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      setMessages((m) => [...m, { role: 'assistant', content: `Error: ${msg}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="p-4 border-b bg-white">
        <h1 className="text-lg font-bold">Chat with ShopAI</h1>
        <p className="text-xs text-slate-500">
          Ask about revenue, products, forecasts, or documents
        </p>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 mt-20">
            Try: “What was my revenue last month?” or “Show me top products”
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center flex-shrink-0">
                <Bot size={16} />
              </div>
            )}
            <div
              className={`max-w-[70%] rounded-lg p-3 text-sm whitespace-pre-wrap ${
                m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white shadow-sm'
              }`}
            >
              {m.content}
              {m.tools && m.tools.length > 0 && (
                <div className="mt-2 text-xs text-slate-500">
                  🔧 Tools: {m.tools.join(', ')}
                </div>
              )}
            </div>
            {m.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center flex-shrink-0">
                <User size={16} />
              </div>
            )}
          </div>
        ))}
        {busy && <div className="text-sm text-slate-500 italic">ShopAI is thinking…</div>}
      </div>

      {error && <div className="px-4 py-2 text-sm text-red-600 bg-red-50">{error}</div>}

      <div className="border-t p-4 bg-white flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask anything about your business…"
          className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={busy}
        />
        <button
          onClick={send}
          disabled={busy || !input.trim()}
          className="bg-slate-900 text-white rounded-lg px-4 py-2 flex items-center gap-2 disabled:opacity-50"
        >
          <Send size={16} /> Send
        </button>
      </div>
    </div>
  )
}