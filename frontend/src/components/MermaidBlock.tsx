import { useEffect, useId, useRef, useState } from 'react'
import mermaid from 'mermaid'

let mermaidInitialized = false

function initMermaidTheme() {
  const dark =
    typeof document !== 'undefined' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  if (!mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'loose',
      theme: dark ? 'dark' : 'default',
    })
    mermaidInitialized = true
  }
}

type Props = {
  chart: string
}

export function MermaidBlock({ chart }: Props) {
  const reactId = useId().replace(/:/g, '')
  const containerRef = useRef<HTMLDivElement>(null)
  const [fallback, setFallback] = useState<string | null>(null)

  useEffect(() => {
    initMermaidTheme()
    const el = containerRef.current
    if (!el) return
    let cancelled = false
    const id = `mmd-${reactId}-${Math.random().toString(36).slice(2, 9)}`

    mermaid
      .render(id, chart)
      .then(({ svg }) => {
        if (!cancelled && el) el.innerHTML = svg
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setFallback(err instanceof Error ? err.message : String(err))
        }
      })

    return () => {
      cancelled = true
    }
  }, [chart, reactId])

  if (fallback !== null) {
    return (
      <pre className="mermaid-fallback" tabIndex={0}>
        <code>{chart}</code>
      </pre>
    )
  }

  return <div ref={containerRef} className="mermaid-block" aria-label="Diagram" />
}
