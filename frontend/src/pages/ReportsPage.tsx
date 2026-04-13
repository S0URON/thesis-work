import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getReportContent, getReports } from '../api/client'
import { getApiBaseUrl } from '../config'
import { MarkdownMessage } from '../components/MarkdownMessage'
import '../App.css'

function basename(path: string): string {
  const s = path.replace(/\\/g, '/')
  const i = s.lastIndexOf('/')
  return i >= 0 ? s.slice(i + 1) : s
}

export default function ReportsPage() {
  const baseUrl = getApiBaseUrl()
  const [paths, setPaths] = useState<string[]>([])
  const [listError, setListError] = useState<string | null>(null)
  const [loadingList, setLoadingList] = useState(true)
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [content, setContent] = useState<string | null>(null)
  const [format, setFormat] = useState<'markdown' | 'json'>('markdown')
  const [loadingContent, setLoadingContent] = useState(false)
  const [contentError, setContentError] = useState<string | null>(null)

  const loadList = useCallback(async () => {
    setLoadingList(true)
    setListError(null)
    try {
      const list = await getReports(baseUrl, 200)
      setPaths(list)
    } catch (e) {
      setListError(e instanceof Error ? e.message : String(e))
      setPaths([])
    } finally {
      setLoadingList(false)
    }
  }, [baseUrl])

  useEffect(() => {
    void loadList()
  }, [loadList])

  const rows = useMemo(
    () =>
      paths.map((p) => ({
        full: p,
        name: basename(p),
      })),
    [paths],
  )

  useEffect(() => {
    if (!selectedName) {
      setContent(null)
      setContentError(null)
      return
    }
    let cancelled = false
    setLoadingContent(true)
    setContentError(null)
    setContent(null)
    void getReportContent(baseUrl, selectedName)
      .then((r) => {
        if (cancelled) return
        setContent(r.content)
        setFormat(r.format)
      })
      .catch((e) => {
        if (cancelled) return
        setContentError(e instanceof Error ? e.message : String(e))
      })
      .finally(() => {
        if (!cancelled) setLoadingContent(false)
      })
    return () => {
      cancelled = true
    }
  }, [baseUrl, selectedName])

  let jsonPretty: string | null = null
  if (format === 'json' && content !== null) {
    try {
      jsonPretty = JSON.stringify(JSON.parse(content), null, 2)
    } catch {
      jsonPretty = content
    }
  }

  return (
    <div className="route-page">
      <p className="app-sub page-sub">
        Saved website analysis reports on the server (newest first). API:{' '}
        <code className="base-url">{baseUrl}</code>
      </p>

      <div className="reports-toolbar">
        <button
          type="button"
          className="btn small"
          onClick={() => void loadList()}
          disabled={loadingList}
        >
          Refresh list
        </button>
        <Link to="/" className="reports-back">
          ← Back to chat
        </Link>
      </div>

      {listError && (
        <div className="banner banner-warn" role="status">
          {listError}
        </div>
      )}

      <div className="reports-archive">
        <div className="reports-list-panel">
          <h2 className="reports-list-title">Reports</h2>
          {loadingList && <p className="muted">Loading…</p>}
          {!loadingList && rows.length === 0 && !listError && (
            <p className="muted">No reports in the server reports folder.</p>
          )}
          <ul className="reports-file-list">
            {rows.map(({ full, name }) => (
              <li key={full}>
                <button
                  type="button"
                  className={
                    selectedName === name
                      ? 'reports-file-btn is-active'
                      : 'reports-file-btn'
                  }
                  onClick={() => setSelectedName(name)}
                >
                  {name}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="reports-viewer">
          {!selectedName && (
            <p className="reports-placeholder muted">
              Select a report to read it here.
            </p>
          )}
          {selectedName && loadingContent && (
            <p className="muted">Loading report…</p>
          )}
          {contentError && (
            <div className="msg-bubble msg-error">{contentError}</div>
          )}
          {selectedName && !loadingContent && !contentError && content !== null && (
            <>
              <h2 className="reports-viewer-title">{selectedName}</h2>
              {format === 'markdown' ? (
                <div className="msg-bubble assistant-text reports-md">
                  <MarkdownMessage content={content} />
                </div>
              ) : (
                <pre className="reports-json-pre">{jsonPretty}</pre>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
