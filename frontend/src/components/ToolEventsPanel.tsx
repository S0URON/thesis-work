import { useState } from 'react'
import type { ToolEvent } from '../api/types'

type Props = {
  events: ToolEvent[]
}

function formatOutput(out: unknown): string {
  if (out === undefined || out === null) return ''
  if (typeof out === 'string') return out
  try {
    return JSON.stringify(out, null, 2)
  } catch {
    return String(out)
  }
}

export function ToolEventsPanel({ events }: Props) {
  const [open, setOpen] = useState(true)

  if (!events.length) return null

  return (
    <div className="tool-events">
      <button
        type="button"
        className="tool-events-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        Activity ({events.length} tool{events.length === 1 ? '' : 's'})
      </button>
      {open && (
        <ol className="tool-events-list">
          {events.map((ev, i) => (
            <li key={i} className="tool-event-item">
              <div className="tool-event-head">
                <span className="tool-name">{ev.name ?? '(unknown)'}</span>
                {ev.cached !== undefined && (
                  <span className="tool-meta">
                    {ev.cached ? 'cached' : 'fresh'}
                  </span>
                )}
                {ev.duration_seconds !== undefined && (
                  <span className="tool-meta">
                    {ev.duration_seconds.toFixed(2)}s
                  </span>
                )}
              </div>
              {ev.args !== undefined && (
                <details className="tool-detail">
                  <summary>Arguments</summary>
                  <pre>{formatOutput(ev.args)}</pre>
                </details>
              )}
              {ev.saved_path && (
                <p className="tool-saved">
                  Saved: <code>{ev.saved_path}</code>
                </p>
              )}
              {ev.output !== undefined && (
                <details className="tool-detail">
                  <summary>Output</summary>
                  <pre className="tool-output">{formatOutput(ev.output)}</pre>
                </details>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
