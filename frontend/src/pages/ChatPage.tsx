import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getHealth,
  getOutputs,
  getReports,
  getStats,
  postChat,
  postSessionClear,
} from '../api/client'
import type { ToolEvent } from '../api/types'
import { getApiBaseUrl, SESSION_STORAGE_KEY } from '../config'
import { MarkdownMessage } from '../components/MarkdownMessage'
import { ToolEventsPanel } from '../components/ToolEventsPanel'
import '../App.css'

type UserMessage = { role: 'user'; content: string }

type AssistantMessage = {
  role: 'assistant'
  content: string
  toolEvents?: ToolEvent[]
  error?: string
  reportPath?: string
}

type ChatMessage = UserMessage | AssistantMessage

function loadSessionId(): string | null {
  try {
    return localStorage.getItem(SESSION_STORAGE_KEY)
  } catch {
    return null
  }
}

function saveSessionId(id: string) {
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
}

function clearStoredSession() {
  try {
    localStorage.removeItem(SESSION_STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

export default function ChatPage() {
  const baseUrl = getApiBaseUrl()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(() =>
    loadSessionId(),
  )
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState<{
    status: string
    ready: boolean
  } | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [stats, setStats] = useState<unknown>(null)
  const [statsError, setStatsError] = useState<string | null>(null)
  const [reports, setReports] = useState<string[]>([])
  const [outputs, setOutputs] = useState<string[]>([])
  const [listsError, setListsError] = useState<string | null>(null)
  const listEndRef = useRef<HTMLDivElement>(null)
  const formRef = useRef<HTMLFormElement>(null)

  const scrollToBottom = () => {
    listEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const refreshHealth = useCallback(async () => {
    try {
      const h = await getHealth(baseUrl)
      setHealth(h)
      setHealthError(null)
    } catch (e) {
      setHealth(null)
      setHealthError(e instanceof Error ? e.message : String(e))
    }
  }, [baseUrl])

  const refreshStats = useCallback(async () => {
    try {
      const s = await getStats(baseUrl)
      setStats(s)
      setStatsError(null)
    } catch (e) {
      setStatsError(e instanceof Error ? e.message : String(e))
    }
  }, [baseUrl])

  const refreshLists = useCallback(async () => {
    try {
      const [r, o] = await Promise.all([
        getReports(baseUrl, 10),
        getOutputs(baseUrl),
      ])
      setReports(r)
      setOutputs(o)
      setListsError(null)
    } catch (e) {
      setListsError(e instanceof Error ? e.message : String(e))
    }
  }, [baseUrl])

  useEffect(() => {
    void refreshHealth()
    const t = window.setInterval(() => void refreshHealth(), 15000)
    return () => window.clearInterval(t)
  }, [refreshHealth])

  useEffect(() => {
    void refreshStats()
    void refreshLists()
  }, [refreshStats, refreshLists])

  const ready = health?.ready !== false

  async function handleSend(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading || !ready) return

    setInput('')
    setMessages((m) => [...m, { role: 'user', content: text }])
    setLoading(true)

    try {
      const body =
        sessionId !== null
          ? { message: text, session_id: sessionId }
          : { message: text }

      const data = await postChat(baseUrl, body)

      if (data.session_id) {
        setSessionId(data.session_id)
        saveSessionId(data.session_id)
      }

      if (data.error) {
        setMessages((m) => [
          ...m,
          {
            role: 'assistant',
            content: '',
            error: data.error,
            toolEvents: data.tool_events,
          },
        ])
      } else {
        setMessages((m) => [
          ...m,
          {
            role: 'assistant',
            content: data.assistant_text ?? '',
            toolEvents: data.tool_events,
            reportPath: data.report_saved_path,
          },
        ])
      }

      void refreshStats()
      void refreshLists()
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: '',
          error: msg,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleClearThread() {
    if (sessionId) {
      try {
        await postSessionClear(baseUrl, sessionId)
      } catch {
        /* still start fresh client-side */
      }
    }
    const next = crypto.randomUUID()
    setSessionId(next)
    saveSessionId(next)
    setMessages([])
  }

  async function handleNewSessionOnly() {
    clearStoredSession()
    setSessionId(null)
    setMessages([])
  }

  return (
    <div className="route-page">
      <p className="app-sub page-sub">
        Chat with the website-analysis agent. API:{' '}
        <code className="base-url">{baseUrl}</code>
      </p>

      {healthError && (
        <div className="banner banner-warn" role="status">
          Health check failed: {healthError}
        </div>
      )}
      {health && !health.ready && (
        <div className="banner banner-warn" role="status">
          Agent not ready ({health.status}). Sending chat may return 503 — check
          MCP connection on the server.
        </div>
      )}
      <div className="app-body">
        <main className="chat-panel">
          <div className="messages" aria-live="polite">
            {messages.length === 0 && (
              <p className="empty-hint">
                Ask for an analysis and include a URL, e.g. “Summarize
                https://example.com”.
              </p>
            )}
            {messages.map((msg, idx) =>
              msg.role === 'user' ? (
                <div key={idx} className="msg msg-user">
                  <div className="msg-label">You</div>
                  <div className="msg-bubble user-text">{msg.content}</div>
                </div>
              ) : (
                <div key={idx} className="msg msg-assistant">
                  <div className="msg-label">Assistant</div>
                  {msg.reportPath && (
                    <div className="report-banner">
                      Report saved on server:{' '}
                      <code>{msg.reportPath}</code>
                    </div>
                  )}
                  {msg.error ? (
                    <div className="msg-bubble msg-error">{msg.error}</div>
                  ) : (
                    <div className="msg-bubble assistant-text">
                      <MarkdownMessage content={msg.content} />
                    </div>
                  )}
                  {msg.toolEvents && msg.toolEvents.length > 0 && (
                    <ToolEventsPanel events={msg.toolEvents} />
                  )}
                </div>
              ),
            )}
            {loading && (
              <div className="msg msg-assistant loading-row">
                <div className="msg-label">Assistant</div>
                <div className="loading-inline" aria-busy="true">
                  <span className="spinner" aria-hidden />
                  Running agent (no streaming — this may take a while)…
                </div>
              </div>
            )}
            <div ref={listEndRef} />
          </div>

          <form
            ref={formRef}
            className="composer"
            onSubmit={handleSend}
          >
            <textarea
              className="composer-input"
              rows={3}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message (include a URL to analyze)…"
              disabled={loading || !ready}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  formRef.current?.requestSubmit()
                }
              }}
            />
            <div className="composer-actions">
              <button
                type="submit"
                className="btn primary"
                disabled={loading || !input.trim() || !ready}
              >
                Send
              </button>
            </div>
          </form>
        </main>

        <aside className="side-panel">
          <section className="side-section">
            <h2>Session</h2>
            <p className="mono small">
              {sessionId ?? '(new thread on first message)'}
            </p>
            <div className="btn-row">
              <button
                type="button"
                className="btn"
                onClick={() => void handleClearThread()}
              >
                Clear &amp; new ID
              </button>
              <button
                type="button"
                className="btn ghost"
                onClick={() => void handleNewSessionOnly()}
              >
                Forget session
              </button>
            </div>
          </section>

          <section className="side-section">
            <h2>Health</h2>
            {health ? (
              <p>
                <span
                  className={
                    health.ready ? 'status-dot ok' : 'status-dot bad'
                  }
                />{' '}
                {health.status} — {health.ready ? 'ready' : 'not ready'}
              </p>
            ) : (
              <p className="muted">…</p>
            )}
            <button
              type="button"
              className="btn small"
              onClick={() => void refreshHealth()}
            >
              Refresh
            </button>
          </section>

          <section className="side-section">
            <div className="side-head">
              <h2>Stats</h2>
              <button
                type="button"
                className="btn small"
                onClick={() => void refreshStats()}
              >
                Refresh
              </button>
            </div>
            {statsError && (
              <p className="side-error">{statsError}</p>
            )}
            {stats !== null && !statsError && (
              <pre className="stats-pre">{JSON.stringify(stats, null, 2)}</pre>
            )}
          </section>

          <section className="side-section">
            <div className="side-head">
              <h2>Reports</h2>
              <button
                type="button"
                className="btn small"
                onClick={() => void refreshLists()}
              >
                Refresh
              </button>
            </div>
            {listsError && (
              <p className="side-error">{listsError}</p>
            )}
            <ul className="path-list">
              {reports.map((p) => (
                <li key={p}>
                  <code title={p}>{p}</code>
                </li>
              ))}
            </ul>
            {reports.length === 0 && !listsError && (
              <p className="muted">No paths listed.</p>
            )}
            <p className="side-link">
              <Link to="/reports">Open report archive →</Link>
            </p>
          </section>

          <section className="side-section">
            <h2>Outputs</h2>
            <ul className="path-list">
              {outputs.map((p) => (
                <li key={p}>
                  <code title={p}>{p}</code>
                </li>
              ))}
            </ul>
            {outputs.length === 0 && !listsError && (
              <p className="muted">No paths listed.</p>
            )}
          </section>
        </aside>
      </div>
    </div>
  )
}
