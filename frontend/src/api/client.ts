import type {
  ChatRequest,
  ChatResponse,
  HealthResponse,
} from './types'

async function parseJsonSafe(res: Response): Promise<unknown> {
  const text = await res.text()
  if (!text) return {}
  try {
    return JSON.parse(text) as unknown
  } catch {
    return { raw: text }
  }
}

function getErrorDetail(data: unknown): string | undefined {
  if (data && typeof data === 'object' && 'detail' in data) {
    const d = (data as { detail: unknown }).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d[0] && typeof d[0] === 'object' && 'msg' in d[0]) {
      return String((d[0] as { msg: string }).msg)
    }
  }
  return undefined
}

export async function postChat(
  baseUrl: string,
  body: ChatRequest,
): Promise<ChatResponse> {
  const res = await fetch(`${baseUrl}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await parseJsonSafe(res)

  if (res.status === 503) {
    throw new Error(
      'Service unavailable (503): agent or MCP not ready. Check GET /api/health.',
    )
  }

  if (!res.ok) {
    throw new Error(
      getErrorDetail(data) ?? `Request failed: ${res.status} ${res.statusText}`,
    )
  }

  return data as ChatResponse
}

export async function postSessionClear(
  baseUrl: string,
  sessionId: string,
): Promise<void> {
  const res = await fetch(`${baseUrl}/api/session/clear`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  })
  const data = await parseJsonSafe(res)
  if (!res.ok) {
    throw new Error(
      getErrorDetail(data) ?? `Clear failed: ${res.status} ${res.statusText}`,
    )
  }
}

export function normalizePathList(data: unknown): string[] {
  if (Array.isArray(data)) {
    return data.filter((x): x is string => typeof x === 'string')
  }
  if (data && typeof data === 'object') {
    const o = data as Record<string, unknown>
    const keys = ['paths', 'reports', 'outputs', 'files', 'items'] as const
    for (const k of keys) {
      const arr = o[k]
      if (Array.isArray(arr)) {
        return arr.filter((x): x is string => typeof x === 'string')
      }
    }
  }
  return []
}

export async function getReports(baseUrl: string): Promise<string[]> {
  const res = await fetch(`${baseUrl}/api/reports`)
  const data = await parseJsonSafe(res)
  if (!res.ok) {
    throw new Error(
      getErrorDetail(data) ?? `Reports failed: ${res.status} ${res.statusText}`,
    )
  }
  return normalizePathList(data)
}

export async function getOutputs(baseUrl: string): Promise<string[]> {
  const res = await fetch(`${baseUrl}/api/outputs`)
  const data = await parseJsonSafe(res)
  if (!res.ok) {
    throw new Error(
      getErrorDetail(data) ?? `Outputs failed: ${res.status} ${res.statusText}`,
    )
  }
  return normalizePathList(data)
}

export async function getStats(baseUrl: string): Promise<unknown> {
  const res = await fetch(`${baseUrl}/api/stats`)
  const data = await parseJsonSafe(res)
  if (!res.ok) {
    throw new Error(
      getErrorDetail(data) ?? `Stats failed: ${res.status} ${res.statusText}`,
    )
  }
  return data
}

export async function getHealth(baseUrl: string): Promise<HealthResponse> {
  const res = await fetch(`${baseUrl}/api/health`)
  const data = await parseJsonSafe(res)
  if (!res.ok) {
    throw new Error(`Health failed: ${res.status} ${res.statusText}`)
  }
  return data as HealthResponse
}
